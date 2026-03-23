from models.patient import Patient
from routes.patient_routes import get_patients

def run():
    print('Patient Management System Initialized')
    print('Loaded:', get_patients())

if __name__ == '__main__':
    run()