# Optional deployment and rollback notes

## Included deployment configuration

The repository contains:

- `render.yaml`: Render Blueprint configuration for a Python web service.
- `Procfile`: process start command for platforms that read a Procfile.
- `/api/health`: lightweight health-check endpoint.

The application reads the hosting platform's `PORT` environment variable and binds to `0.0.0.0`, which is required for a hosted web service.

## Optional Render deployment

1. Push the project to the public GitHub repository first.
2. Sign in to Render and choose **New → Blueprint**.
3. Connect the GitHub repository `PranathiM15/ecommerce-customer-segmentation-recommender`.
4. Render reads the root `render.yaml`. Review the service name and configuration, then create the service.
5. Wait until the service is marked live, open its URL, and check that the dashboard loads and `/api/health` returns an `ok` response.
6. Save the public URL and capture a screenshot of the working deployed dashboard for your submission record.

The local CSV upload is stored on the service filesystem. Do not treat a free hosted instance's local filesystem as permanent storage. For reliable hosted use with your own data, use a persistent storage service or re-upload the CSV after a restart/deploy. The included synthetic demo dataset is bundled with the code and is available on startup.

## Safe rollback procedure

Git history provides the rollback record. Before a significant change, make sure the current working version is committed:

```powershell
git status
git add .
git commit -m "Save stable ORBIT version"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

If a later commit breaks the app, find its commit ID:

```powershell
git log --oneline -5
```

Revert the bad commit without rewriting shared history (replace the placeholder with the actual commit ID):

```powershell
git revert COMMIT_ID
git push origin main
```

For a hosted Render service connected to this GitHub branch, the new revert commit triggers a normal deployment. Confirm the health endpoint and dashboard after the deployment completes.

## Rollback evidence to save for the internship portal

This file documents the rollback procedure; it does not claim a deployment or rollback has already happened. After you perform the optional deployment and rollback test, save:

1. The stable version's Git commit hash and tag (`v1.0.0`).
2. The later commit hash that introduced the issue (if testing a rollback).
3. The revert commit hash shown by `git log --oneline -5`.
4. A screenshot of the app working after the revert, plus the deployment event/history page if hosted.
5. The deployed URL and the date you checked it.

Do not invent commit hashes, deployment URLs, or rollback screenshots. Only submit evidence you actually captured.
