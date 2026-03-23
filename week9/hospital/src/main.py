from fastapi import FastAPI

app = FastAPI()

@app.get("/patients")
async def get_patients(): return {"message": "List patients"}

@app.post("/patients")
async def create_patient(): return {"message": "Create patient"}

@app.get("/appointments")
async def get_appointments(): return {"message": "List appointments"}

@app.post("/appointments")
async def create_appointment(): return {"message": "Create appointment"}

@app.get("/doctors")
async def get_doctors(): return {"message": "List doctors"}

@app.post("/doctors")
async def create_doctor(): return {"message": "Create doctor"}
