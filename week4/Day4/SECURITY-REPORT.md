# SECURITY REPORT - Day 4

## Week 4 - Advanced Backend Engineering

---

## 1. SECURITY MIDDLEWARE IMPLEMENTED

- Helmet (Security Headers)
- CORS Configuration
- Rate Limiting
- Parameter Pollution Prevention (HPP)

---

## 2. VULNERABILITIES TESTED

### Validation

- Valid Product(Should work)

curl -X POST http://localhost:3000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Samsung Galaxy S24","price":899,"category":"Electronics","createdBy":"697b6c05c0e6810afe491147","tags":["android","smartphone"]}'

  ![ss1](day4/test1.png)

- Missing Required Fields (Should FAIL - 400)

curl -X POST http://localhost:3000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"category":"Electronics"}'

  ![ss1](day4/test2.png)

---

### Security 

- XSS Attack - Script Tag (Should SANITIZE)

curl -X POST http://localhost:3000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"<script>alert(\"XSS\")</script>Product","price":100,"category":"Test","createdBy":"697b6c05c0e6810afe491147"}'

  ![ss1](day4/test3.png)

---

-  NoSQL Injection - $gt Operator (Should FAIL - validation)

curl -X POST http://localhost:3000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","price":{"$gt":0},"category":"Test"}'
 
  ![ss1](day4/test4.png)

---

-  Rate Limit Test (too many req)
for i in {1..105}; do 
  echo "Request $i"
  curl -s http://localhost:3000/api/v1/products | grep -o '"success":[^,]*'
done

  ![ss1](day4/test5.png)

---

-  Large Payload (Should FAIL - 413)

curl -X POST http://localhost:3000/api/v1/products \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$(python3 -c 'print("A"*12000)')\",\"price\":100,\"category\":\"Test\"}"

   ![ss1](day4/test6.png)

---

- Check HSTS Header
  
curl -I http://localhost:3000/api/v1/products | grep -i "strict-transport"

   ![ss1](day4/test7.png)

---

- Preflight request (OPTIONS)

curl -X OPTIONS http://localhost:3000/api/v1/products \
  -H "Origin: http://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v

   ![ss1](day4/test8.png)
