from fastapi import FastAPI
from . import database, models, routes

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()
app.include_router(routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
