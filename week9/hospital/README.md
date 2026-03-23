# Hospital Management System API

## Endpoints

### Patients
- GET /patients: Retrieve all patients
- POST /patients: Create a new patient
- GET /patients/{id}: Get patient by ID
- PUT /patients/{id}: Update patient info
- DELETE /patients/{id}: Remove a patient

### Appointments
- GET /appointments: List all appointments
- POST /appointments: Schedule an appointment
- PUT /appointments/{id}: Reschedule/Update appointment
- DELETE /appointments/{id}: Cancel appointment

### Doctors
- GET /doctors: List all doctors
- POST /doctors: Register a doctor
- GET /doctors/{id}: Get doctor details
