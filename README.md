# 🎓Blockchain Certificates – “Secure. Transparent. Immutable.”

A simple blockchain-based certificate management system built with **Python (Flask)**, **Solidity**, and **Ethereum (Ganache for local testing)**.
This project allows you to **issue certificates**, **store them on the blockchain**, and **verify authenticity** using a unique certificate ID.

---

## 🚀 Features
- Issue certificates with **student details, course, and institution**.
- Store certificates on a **local Ethereum blockchain (Ganache)**.
- Verify certificate authenticity via blockchain transaction.
- Download issued certificates as **PDF files**.
- Clean **Flask + Tailwind CSS frontend**.

---

## 📦 Prerequisites
- python
- node (npm)

---

### Note
Since there are no secrets in this project you can rename .env.example as .env or run this command
```bash
copy .env.example .env # (WINDOWS)
cp .env.example .env # (LINUX)
```

---

## How to run?
Install ganache
``` bash
npm install -g ganache
```

``` bash
# Start Ganache (local Ethereum blockchain)
ganache --port 8545 --deterministic
```

Create a virtual environment for python
```bash
python -m venv venv
```

Activate the virtual environment
``` bash
.\venv\Scripts\activate # (WINDOWS)
source venv/bin/activate # (LINUX)
```

Python dependencies (install inside virtual environment):
``` bash
pip install -r requirements.txt
```
 Run the following commands
```bash

# Deploy Smart Contract
python deploy_contract.py

# Run Flask App
python app.py
```

To deactivate the virtual env (after completion)
``` bash
deactivate
```

---

Now open 👉 http://127.0.0.1:5000 in your browser.