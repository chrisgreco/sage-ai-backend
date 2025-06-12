# Welcome to your Lovable project

## Project info

**URL**: https://lovable.dev/projects/1e934c03-5a1a-4df1-9eed-2c278b3ec6a8

## Docker Deployment on Render

This project is configured to be deployed on Render using Docker. Follow these steps to set up the deployment:

1. **Push your code to GitHub**
   Make sure your code is pushed to a GitHub repository.

2. **Create a Render account**
   Sign up for a Render account at [render.com](https://render.com) if you don't have one already.

3. **Connect your GitHub repository**
   - Go to the Render dashboard
   - Click "New" and select "Blueprint"
   - Connect your GitHub account if not already connected
   - Select the repository containing this project
   - Configure access permissions as needed

4. **Deploy using the Blueprint**
   The included `render.yaml` file will automatically configure your service:
   - Render will use the Dockerfile to build the application
   - Environment variables from your repository will be used
   - The service will be deployed and accessible via the provided Render URL

5. **Environment Variables**
   - All environment variables from your `.env` file in the `livekit-agents` directory will be copied during build
   - You can also set environment variables directly in the Render dashboard for additional security

6. **Set Up GitHub Actions CI/CD (Optional)**
   - A GitHub Actions workflow is included in `.github/workflows/ci-cd.yml`
   - In your GitHub repository, go to Settings > Secrets and Variables > Actions
   - Add a new repository secret called `RENDER_DEPLOY_HOOK` with the value of your Render deploy hook URL
   - This URL can be found in your Render dashboard under the service's Settings > Deploy Hook
   - Now, every push to the main branch will trigger an automatic deployment to Render

### Local Docker Development

To run the application locally using Docker:

```bash
# Build the Docker image
npm run docker:build

# Run the Docker container
npm run docker:run
```

The application will be available at http://localhost:8080

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/1e934c03-5a1a-4df1-9eed-2c278b3ec6a8) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository using the project's Git URL.
git clone <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/1e934c03-5a1a-4df1-9eed-2c278b3ec6a8) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/tips-tricks/custom-domain#step-by-step-guide)
