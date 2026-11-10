# Publish ORBIT to GitHub from Windows Terminal

Your GitHub profile from the supplied screenshot is `PranathiM15`.

## A. Create the empty public repository

1. Open **https://github.com/new** and sign in to `PranathiM15`.
2. Repository name: `ecommerce-customer-segmentation-recommender`
3. Description: `E-commerce customer segmentation and product recommendation dashboard using RFM, K-Means and cosine similarity.`
4. Choose **Public**.
5. Leave **Add a README**, **Add .gitignore**, and **Choose a license** set to **None / not selected** because those files already exist in this project folder.
6. Click **Create repository**. Keep the repository page open.

Expected repository address:

`https://github.com/PranathiM15/ecommerce-customer-segmentation-recommender`

## B. Check Git before running commands

Open PowerShell in the extracted project folder (the folder containing `app.py`). Run:

```powershell
git --version
```

If a Git version is displayed, continue to section C.

If PowerShell says `git` is not recognized:

1. Install Git for Windows from the official page: https://git-scm.com/install/windows
2. During setup, keep the option that makes Git available from the command line / PATH.
3. Finish setup and close **all** open PowerShell and VS Code terminal windows.
4. Open a new PowerShell window in the project folder and run `git --version` again.

## C. Push the project (run each command in order)

Make sure the terminal path is the project folder. You can check it with `Get-Location`.

```powershell
git init
git add .
git status
git commit -m "Build e-commerce customer segmentation and recommendation app"
git branch -M main
git remote add origin https://github.com/PranathiM15/ecommerce-customer-segmentation-recommender.git
git push -u origin main
```

When Git asks you to authenticate, complete the sign-in flow in the browser / Git Credential Manager. Do not paste a password or access token into this project or into chat.

Refresh the GitHub repository page. You should see `app.py`, `analytics.py`, `index.html`, `styles.css`, `app.js`, `online_retail_sample.csv`, `README.md`, and the other project files.

## D. Fix common Git issues

### Message: `remote origin already exists`

Do not run `git remote add origin` a second time. Replace the remote URL instead:

```powershell
git remote set-url origin https://github.com/PranathiM15/ecommerce-customer-segmentation-recommender.git
git remote -v
git push -u origin main
```

### Message: `src refspec main does not match any`

This usually means there is no commit yet. Run:

```powershell
git add .
git commit -m "Initial ORBIT project"
git branch -M main
git push -u origin main
```

### Message: `Author identity unknown`

Set the name and the email associated with your GitHub account, then retry the commit:

```powershell
git config --global user.name "Pranathi M"
git config --global user.email "YOUR_GITHUB_VERIFIED_EMAIL"
git commit -m "Build e-commerce customer segmentation and recommendation app"
```

Replace `YOUR_GITHUB_VERIFIED_EMAIL` with your own verified GitHub email address. Do not use the placeholder literally.

### Message: `failed to push some refs` / `fetch first`

This can happen when a starter file was created on GitHub. The safest option for this guide is to create the GitHub repository empty (section A). If you already created a remote README and the push is rejected, inspect the repository page before merging. Do not force-push over files you need.

### Message: Git is installed but PowerShell still cannot find it

Close and reopen PowerShell after installing Git. If it still fails, rerun the official Git for Windows installer and select the command-line / PATH option. Verify using `git --version` before continuing.

## E. Update the repository after later changes

From the same project folder:

```powershell
git add .
git commit -m "Update customer analytics dashboard"
git push
```

Before publishing, check that `uploaded_transactions.csv` is not staged. It is listed in `.gitignore` by design.
