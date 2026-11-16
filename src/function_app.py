import json
import logging
import os
import re

import azure.functions as func
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.queue.aio import QueueClient
from azurefunctions.extensions.http.fastapi import JSONResponse, Request

from azure_functions_agents import HostedSkill, HostedSkillFunctionApp

app = HostedSkillFunctionApp()

TRIAGED_CONTAINER = "triaged"
ALERT_QUEUE = "p1-alerts"
_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _parse_feedback(raw: str) -> tuple[str | None, str | None, str]:
    """Accepts {"id", "customer", "text"} JSON or plain text. Returns (id, customer, text)."""
    try:
        data = json.loads(raw)
    except ValueError:
        return None, None, raw.strip()
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return None, None, raw.strip()
    feedback_id = data.get("id") if isinstance(data.get("id"), str) else None
    customer = data.get("customer") if isinstance(data.get("customer"), str) else None
    return feedback_id, customer, data["text"].strip()


def _build_prompt(customer: str | None, text: str) -> str:
    return f"Customer: {customer or 'unknown'}\n\nFeedback:\n{text}"


async def _classify(skill: HostedSkill, customer: str | None, text: str) -> dict:
    result = await skill.run(_build_prompt(customer, text))
    return json.loads(result.content)


async def _save(record: dict) -> None:
    async with DefaultAzureCredential(
        managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID")
    ) as credential:
        async with BlobServiceClient(
            os.environ["AzureWebJobsStorage__blobServiceUri"], credential=credential
        ) as blobs:
            await blobs.get_blob_client(
                TRIAGED_CONTAINER, f"{record['feedback_id']}.json"
            ).upload_blob(
                json.dumps(record, indent=2),
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json"),
            )

        # At-least-once: a retry after this point can send a duplicate alert.
        # Consumers should de-duplicate by feedback_id.
        if record["priority"] == "P1":
            async with QueueClient(
                os.environ["AzureWebJobsStorage__queueServiceUri"],
                ALERT_QUEUE,
                credential=credential,
            ) as alerts:
                await alerts.send_message(
                    json.dumps(
                        {
                            "feedback_id": record["feedback_id"],
                            "customer": record["customer"],
                            "summary": record["summary"],
                            "priority_reason": record["priority_reason"],
                        }
                    )
                )


@app.queue_trigger(arg_name="msg", queue_name="feedback-in", connection="AzureWebJobsStorage")
@app.hosted_skill(arg_name="skill", agent_name="feedback_classifier")
async def triage_queue(msg: func.QueueMessage, skill: HostedSkill) -> None:
    feedback_id, customer, text = _parse_feedback(msg.get_body().decode("utf-8"))
    if not text:
        raise ValueError(f"Queue message {msg.id} has no feedback text.")
    if not feedback_id or not _ID_PATTERN.match(feedback_id):
        feedback_id = msg.id

    triage = await _classify(skill, customer, text)
    record = {"feedback_id": feedback_id, "customer": customer, "text": text, **triage}
    await _save(record)
    logging.info("Triaged %s as %s/%s", feedback_id, triage["category"], triage["priority"])


@app.route(route="triage", methods=["POST"])
@app.hosted_skill(arg_name="skill", agent_name="feedback_classifier")
async def triage_http(req: Request, skill: HostedSkill) -> JSONResponse:
    try:
        body = await req.json()
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError
    except (AttributeError, ValueError):
        return JSONResponse({"error": "Request JSON must include nonblank 'text'."}, status_code=400)

    customer = body.get("customer") if isinstance(body.get("customer"), str) else None
    return JSONResponse(await _classify(skill, customer, text.strip()))
