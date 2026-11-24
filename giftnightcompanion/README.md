# Afterglow — Sıla & Mafuyu

A responsive, self-contained anniversary-night companion. Open `index.html` locally, or publish this folder with GitHub Pages. Includes live Ankara/Moscow clocks, bilingual Turkish/English love notes, relaxing audio mix, a guided breathing animation, a sleep timer, and an optional realtime private-room chat.

## Publish on GitHub Pages

In the repository settings, open **Pages**, select **Deploy from a branch**, choose the current branch and `/giftnightcompanion` as the folder if GitHub offers it. GitHub Pages commonly only offers the repository root or `/docs`; if so, either copy this folder's contents into `docs/`, or add a workflow to publish this folder. A minimal workflow is:

```yaml
name: Publish Afterglow
on:
  push:
    branches: [main] # change to your publishing branch
    paths: ["giftnightcompanion/**", ".github/workflows/afterglow-pages.yml"]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: giftnightcompanion
      - id: deployment
        uses: actions/deploy-pages@v4
```

Enable **GitHub Actions** as the Pages source under Settings → Pages. Adjust the branch filter to whichever branch you intend to publish. The workflow publishes only this folder.

## Optional shared chat (Firebase; free tier is usually enough)

GitHub Pages is static hosting and cannot run a persistent chat server. This page uses Firebase's hosted Firestore database for realtime messages; no server process or GitHub secret is needed. Both people need the same Firebase project and room code.

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com), add a **Web app**, and copy its Firebase web configuration.
2. In **Build → Firestore Database**, create a database. For production, use production mode and publish rules like the following; the page deliberately only accepts bounded-size text messages. Firestore's rules cannot keep a room code secret from someone who learns it, so use an unguessable private room code and do not share the page/config publicly.
3. In Firebase **Authentication → Sign-in method**, enable **Anonymous** only if you decide to add authentication later. This current no-login version does not use Firebase Auth: Firestore rules below allow reads/writes to anyone who knows a room. This is convenient for a gift but is not identity verification or end-to-end encryption. For a more private deployment, add Firebase anonymous sign-in and restrict rules to authenticated users, then update the client to sign in.
4. Open the page, choose **Settings**, paste the web config JSON, set a shared room code (3–48 letters/numbers/dashes/underscores), and enter your display name. Do the same on the other device. The config is saved in that browser's local storage only. Never paste a Firebase service-account credential or private key here.

Example Firestore rules for this simple, room-code-as-access-token setup (use a hard-to-guess room code; anyone who obtains it can read and write):

```text
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /rooms/{room}/messages/{message} {
      allow read: if room.matches('^[A-Za-z0-9_-]{3,48}$');
      allow create: if room.matches('^[A-Za-z0-9_-]{3,48}$')
        && request.resource.data.keys().hasOnly(['text', 'name', 'createdAt'])
        && request.resource.data.text is string
        && request.resource.data.text.size() > 0
        && request.resource.data.text.size() <= 1000
        && request.resource.data.name is string
        && request.resource.data.name.size() > 0
        && request.resource.data.name.size() <= 32
        && request.resource.data.createdAt == request.time;
      allow update, delete: if false;
    }
  }
}
```

These rules are intentionally described honestly: the room string is not a secure login, and browser-to-Firebase messages are not end-to-end encrypted. Firebase config is designed to be public; enforce access with Firestore rules, and configure Firebase App Check / authenticated rules for a public deployment. A small allowance on Firestore reads/writes may be billable if quotas are exceeded; set budget alerts.

## Notes

- Ambient audio starts only after you press a sound button (browser autoplay policy); internet access is needed for the hosted sound clips and Google Fonts.
- Turkish/English preference and chat setup are saved locally in each browser.
- Chat messages are ordered by Firestore server timestamps, and the client displays the latest 100 messages.
- The original supplied file was a `.txt` HTML document. This folder is the standalone revamped version; the original is left untouched.
