# Customer feedback triage with Azure Functions hosted skills

This sample classifies customer feedback by using an Azure Functions hosted skill. It's built on the [functions-quickstart-serverless-agents-azd](https://github.com/Azure-Samples/functions-quickstart-serverless-agents-azd) template, and you deploy it with the Azure Developer CLI (`azd`).

> [!NOTE]
> Azure Functions hosted skills is in preview and supports Python only.

## What it does

Each piece of feedback is classified by category, sentiment, and priority (P1–P3). The hosted skill also writes a one-line summary and a suggested reply.

- **Queue path (`triage_queue`)**: A message in the `feedback-in` queue triggers the function. The function saves the result as JSON in the `triaged` blob container. For P1 feedback, it also sends an alert to the `p1-alerts` queue.
- **HTTP path (`triage_http`)**: `POST /triage` returns the classification right away.

```
feedback-in queue ─► triage_queue ─► feedback_classifier skill (gpt-4.1)
                                   ├─► triaged/{id}.json
                                   └─► p1-alerts queue (P1 only)

POST /triage ─► triage_http ─► feedback_classifier skill ─► JSON response
```

## Project structure

| Path | Purpose |
|---|---|
| `src/feedback_classifier.agent.md` | The hosted skill: instructions and the JSON response schema |
| `src/skills/feedback-triage/SKILL.md` | Triage rules for category, sentiment, and priority |
| `src/function_app.py` | Queue and HTTP functions that call the skill through the Hosted Skill binding |
| `src/host.json` | Queue settings: plain-text messages, three retries |
| `src/main.agent.md` | Built-in chat agent from the template, kept for debugging |
| `infra/` | Bicep files that `azd up` deploys |

## Prerequisites

- An Azure subscription where you have the Owner role
- At least 200K TPM of gpt-4.1 GlobalStandard quota
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) and [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- One of these regions: `centralus`, `eastus`, `eastus2`, `northcentralus`, `southcentralus`, `westus`

## Deploy

```powershell
azd auth login
azd up
```

When prompted, enter an environment name, select your subscription, and select a region. `azd up` creates the resource group `rg-<environment-name>` and everything in it, then deploys the code.

## Test the HTTP endpoint

```powershell
$app = azd env get-value AZURE_FUNCTION_NAME
$rg  = "rg-$(azd env get-value AZURE_ENV_NAME)"
$key = az functionapp function keys list -g $rg -n $app --function-name triage_http --query default -o tsv
$body = @{ customer = "Contoso"; text = "Your app charged my card twice this month. Fix this or I'm cancelling." } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://$app.azurewebsites.net/triage?code=$key" -Body $body -ContentType "application/json"
```

Expected result: `Billing`, `Negative`, `P1`.

## Test the queue path

1. In the Azure portal, open the storage account in the resource group and go to **Queues** > **feedback-in**.
2. Select **Add message**, paste the following JSON, and **clear** the **Encode the message body in Base64** checkbox:

   ```json
   {"id":"fb-001","customer":"Contoso","text":"Since this morning's update the app crashes on login and none of our 40 users can work."}
   ```

3. After about a minute, open **Containers** > **triaged** and select `fb-001.json`. The `p1-alerts` queue contains one alert.

## Clean up

```powershell
azd down --purge
```

## Learn more

- [Azure Functions hosted skills overview](https://learn.microsoft.com/azure/azure-functions/functions-hosted-skills)
- [Azure Developer CLI overview](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview)

## License

MIT. Based on a Microsoft sample. See [LICENSE](LICENSE).
