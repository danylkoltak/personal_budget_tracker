# personal_budget_tracker (FastApi framework, Postgres database, Docker)

Main functionality:

User register and login (via jwt token and hashed password)
Creating, deleting, and editing Categories
Adding, deleting, and editing Expenses for the corresponding Category
Get total sum of all Expenses for a specific Category
Get total sum for all Categories
Logout with deleting access token from cookies

The Docker container "personal_budget_tracker" includes two services: "db" (name of the container: db, with database configuration) and "app" (name of the container: personal-budget-app, with the logic of the app itself and admin environment)

To launch the app locally and gain access to the fucnctionality, follow these steps:

1. Clone the project to your local machine from the corresponding git repository

2. Paste .env file into the root folder on the same level as main.py. (.env must contain variebles for DATABASE_URL=, ACCESS_TOKEN_EXPIRE_MINUTES=, SECRET_KEY=, SUPERUSER_USERNAME=, and SUPERUSER_PASSWORD=)

3.  Run "docker-compose build" command in the terminal (assuming you have Docker installed)

4. Run "docker-compose up" or "docker-compose up -d" command to make the container running. In the terminal, you will see:
 ✔ Network personal_budget_tracker_default Created
 ✔ Volume "personal_budget_pgdata" Created
 ✔ Container db Healthy
 ✔ Container personal-budget-app Started

 5. After that, open the browser and on "http://localhost:8000/" or "http://127.0.0.1:8000/" you will see the home page of the app, where you can register and log in as a user, and enjoy the functionality of the app
 
 6. On "http://localhost:8000/admin" or "http://127.0.0.1:8000/admin" you will gain access to the admin environment as a superuser which is automatically created with the credentials pointed in .env file

 7. On http://localhost:8000/docs# or http://127.0.0.1:8000/docs#/ you will see all API entry points and Schemas