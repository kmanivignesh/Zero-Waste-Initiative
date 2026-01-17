# 🌱 Zero Waste Initiative  
### AI-Powered Priority-Based Food Donation Platform

---

## 📌 Project Overview

**Zero Waste Initiative** is a web-based application built using **Django** to reduce food wastage by connecting **food donors** (restaurants, canteens) with **receivers** (NGOs, shelters).

The platform uses a **Machine Learning regression model** to calculate a **priority score** for each food donation based on urgency factors such as expiry time and quantity.  
An **Explainable AI (XAI) chatbot** is integrated to explain these priority decisions, ensuring transparency and responsible AI usage.

---

## 🎯 Problem Statement

Urban areas generate large amounts of surplus food daily, which is often wasted due to:
- Lack of coordination between donors and receivers
- Manual and inefficient pickup scheduling
- No systematic way to evaluate food urgency
- Absence of transparency in prioritization decisions

At the same time, NGOs struggle to access timely food resources.

---

## 💡 Solution

The Zero Waste Initiative provides:
- A centralized food donation platform
- AI-driven priority scoring for urgency-based pickup
- Role-based dashboards for donors, receivers, and admins
- An AI chatbot to explain ML-based priority decisions

---

## 👥 User Roles & Features

### 👤 Donor
- Sign up and login
- Update donor profile
- Create food donation orders
  - Food type
  - Quantity
  - Unit
  - Expiry time
- View donation status
- Receive multiple pickup requests
- Accept one receiver (others are automatically rejected)
- View donor analytics

---

### 🏥 Receiver (NGO)
- Sign up and login
- Update receiver profile and capacity
- View available donations ranked by **priority score**
- Schedule pickups based on urgency
- Track scheduled and completed pickups
- Use **AI Assistant (Chatbot)** to:
  - Ask why a donation is high or low priority
  - Understand AI-generated urgency decisions

---

### 🛠 Admin
- View platform-wide statistics
- Monitor donors, receivers, donations, and pickup schedules
- Access admin analytics dashboard

---

## 🤖 AI & Machine Learning

### 🔹 Priority Scoring Model
A lightweight **regression model** predicts food urgency using:
- Time remaining before expiry
- Quantity of food
- Contextual parameters

**Output:**  
A numeric **priority score** used to rank donations on the receiver dashboard.

---

### 🔹 Explainable AI (Chatbot)
- Implemented as a **floating chatbot icon**
- Available on the **receiver dashboard**
- Explains why a donation received a specific priority score

**Example Response:**
> “This donation has high priority because the food is close to expiry and the quantity is high.”

✔ AI explains decisions  
✔ Humans make final choices  
✔ No automated enforcement  

---

## 🧠 Responsible AI Principles

- **Transparency:** Priority decisions are explained via chatbot
- **Human-in-the-loop:** Donors and receivers control final actions
- **Fairness:** Priority based on food attributes, not user identity
- **Privacy:** Chatbot accessible only to authenticated users

---

## 🏗 System Architecture (High Level)

Donor → Donation Entry
↓
ML Priority Scoring Model
↓
Receiver Dashboard (Ranked Donations)
↓
Pickup Scheduling
↓
Explainable AI Chatbot


---

## 🛠 Technology Stack

| Component | Technology |
|---------|-----------|
Backend | Python, Django |
Database | Relational Database (Oracle / SQLite for development) |
Frontend | HTML, CSS, JavaScript, Bootstrap |
AI / ML | Python, Scikit-Learn, Pandas |
UI | FontAwesome, CSS Animations |

---

## 🌍 Impact & Sustainability

- **SDG 2 – Zero Hunger:** Improves food access for NGOs
- **SDG 12 – Responsible Consumption:** Reduces food wastage
- **SDG 13 – Climate Action:** Lowers methane emissions from food waste

---

## 📸 Application Screens

The project includes screens for:
- Home and login pages
- Donor dashboard and donation form
- Receiver dashboard with priority scores
- AI Assistant (Explainable AI chatbot)
- Admin analytics dashboard

---

## 🚀 How to Run the Project

```bash
# Clone the repository
git clone <repository-url>

# Navigate to project directory
cd zero_waste_initiative

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Start the development server
python manage.py runserver

