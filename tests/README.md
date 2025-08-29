### Testing Procedure

**1. docker compose up -d --build**

This command is commonly used to start all services defined in your compose.yaml file

-d or --detach: Runs the containers in detached mode, meaning they run in the background and you regain control of your terminal.

--no-cache: Disables the image builder cache and enforces a full rebuild from source for all image layers. This ensures that no cached layers are used during the build, so all steps in your Dockerfiles are executed from scratch

--build: Builds images before starting containers. This ensures that any changes in your Dockerfiles or application code are incorporated into the images before the containers are started.

**2. docker exec -it scanner bash**

docker exec: Executes a command in a running container.

-i: Keeps STDIN open, allowing you to interact with the shell.

-t: Allocates a pseudo-TTY, making the session interactive (like a terminal).

scanner: The name (or ID) of the running container you want to access.

bash: The command to run inside the container (in this case, the Bash shell).

**3. python src/scanner.py**

This command starts the scanner app

**docker compose down**

This command stops and removes containers, networks, and the default network created by docker compose up for the services defined in your Compose file

### Additonal Commands

**docker compose build --no-cache**

This command builds or rebuilds the images for the services defined in your Compose file

--no-cache: Disables the image builder cache and enforces a full rebuild from source for all image layers. This ensures that no cached layers are used during the build, so all steps in your Dockerfiles are executed from scratch
