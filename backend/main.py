from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import hashlib

# ML
from sklearn.linear_model import LinearRegression
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= USERS =================
users = {}

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def create_user(password):
    return {
        "password": hash_password(password),

        "appliances": {
            "light": {"power": 10, "count": 2},
            "fan": {"power": 75, "count": 2},
            "ac": {"power": 1500, "count": 1},
            "fridge": {"power": 200, "count": 1}
        },

        "status": {},
        "usage_hours": {},

        "energy": 0,
        "hour": 0,
        "day": 0,

        "hourly": [],
        "daily": [],
        "plans": [],

        "blockchain": [],

        "monthly_budget": 3000,
        "monthly_bills": [],

        "start_date": datetime.now()
    }

# ================= LOGIN =================
@app.post("/login")
def login(user: str, password: str):
    if user not in users:
        users[user] = create_user(password)
        users[user]["status"] = {k: False for k in users[user]["appliances"]}
        users[user]["usage_hours"] = {k: 0 for k in users[user]["appliances"]}
    else:
        if users[user]["password"] != hash_password(password):
            raise HTTPException(401, "Wrong password")

    return {"msg": "login success"}

# ================= POWER =================
def calc_power(u):
    return sum(
        u["appliances"][a]["power"] * u["appliances"][a]["count"]
        for a in u["appliances"] if u["status"][a]
    )

# ================= TN EB BILL (REALISTIC) =================
def calc_bill(units):

    if units == 0:
        return 0

    if units <= 100:
        cost = units * 2
    elif units <= 200:
        cost = 100*2 + (units-100)*3
    elif units <= 500:
        cost = 100*2 + 100*3 + (units-200)*5
    else:
        cost = 100*2 + 100*3 + 300*5 + (units-500)*8

    fixed_charge = 100
    return round(cost + fixed_charge, 2)
# ================= ALERT =================
def get_alert(u):
    active = {
        a: u["appliances"][a]["power"] * u["appliances"][a]["count"]
        for a in u["appliances"] if u["status"][a]
    }

    if not active:
        return "No active appliances"

    high = max(active, key=active.get)
    return f"High usage due to {high.upper()} ({active[high]}W)"

# ================= PLAN =================
def generate_plan(u):
    if not u["daily"]:
        return "Day 1: Collecting data"

    last = u["daily"][-1]
    daily_budget = u["monthly_budget"] / 30
    allowed = daily_budget / 5

    lines = []

    for dev, hrs in u["usage_hours"].items():
        if hrs == 0:
            continue

        reduce_to = max(1, int(hrs * 0.6))

        lines.append(
            f"{dev.upper()}: {hrs} hrs → reduce to {reduce_to} hrs"
        )

    if last > allowed:
        lines.insert(0, f"Exceeded by {round(last-allowed,2)} kWh")
    else:
        lines.insert(0, "Within budget")

    return "\n".join(lines)

# ================= ML PREDICTION =================
def predict(u):
    if len(u["daily"]) < 3:
        return "Collecting data..."

    y = np.array(u["daily"])
    X = np.array(range(len(y))).reshape(-1,1)

    model = LinearRegression()
    model.fit(X, y)

    next_day = model.predict([[len(y)]])[0]
    return round(float(next_day), 2)

# ================= BLOCKCHAIN =================
def add_block(u):
    prev = u["blockchain"][-1]["hash"] if u["blockchain"] else "0"

    date = (u["start_date"] + timedelta(days=u["day"])).date()
    energy = u["energy"]
    bill = calc_bill(energy)

    data = f"{u['day']}{date}{energy}{bill}{prev}"
    h = hashlib.sha256(data.encode()).hexdigest()

    block = {
        "day": u["day"] + 1,
        "date": str(date),
        "energy": round(energy, 2),
        "bill": bill,
        "prev_hash": prev,
        "hash": h
    }

    u["blockchain"].append(block)
    u["daily"].append(energy)

    # monthly summary
    if len(u["daily"]) % 30 == 0:
        total = sum([b["bill"] for b in u["blockchain"][-30:]])
        u["monthly_bills"].append({
            "month": len(u["monthly_bills"]) + 1,
            "expected": u["monthly_budget"],
            "actual": round(total,2)
        })

# ================= STEP =================
@app.get("/step/{user}")
def step(user: str):
    u = users[user]

    power = calc_power(u)

    if power > 0:
        u["energy"] += power / 1000

    # usage tracking
    for a in u["appliances"]:
        if u["status"][a]:
            u["usage_hours"][a] += 1

    u["hourly"].append(u["energy"])
    u["hour"] += 1

    # 11 PM PLAN
    if u["hour"] == 23:
        plan = generate_plan(u)
        u["plans"].append(f"Day {u['day']+1}: {plan}")

    if u["hour"] >= 24:
        add_block(u)

        u["energy"] = 0
        u["hour"] = 0
        u["hourly"] = []
        u["usage_hours"] = {k:0 for k in u["appliances"]}
        u["day"] += 1

    return {"msg": "ok"}

# ================= STATUS =================
@app.get("/status/{user}")
def status(user: str):
    u = users[user]
    power = calc_power(u)

    return {
        "power": power,
        "current": round(power/230,2) if power else 0,
        "energy": round(u["energy"],2),
        "hour": u["hour"],
        "appliances": u["status"]
    }

# ================= TOGGLE =================
@app.get("/toggle/{user}/{device}")
def toggle(user: str, device: str):
    u = users[user]
    u["status"][device] = not u["status"][device]
    return u["status"]

# ================= ADD APPLIANCE =================
@app.post("/add/{user}")
def add(user: str, name: str, power: int, count: int):
    u = users[user]
    u["appliances"][name] = {"power": power, "count": count}
    u["status"][name] = False
    u["usage_hours"][name] = 0
    return {"msg": "added"}

# ================= ANALYTICS =================
@app.get("/analytics/{user}")
def analytics(user: str):
    u = users[user]

    weekly = [
        sum(u["daily"][i:i+7])
        for i in range(0, len(u["daily"]), 7)
    ][:4]

    monthly = [
        sum(weekly[i:i+4])
        for i in range(0, len(weekly), 4)
    ]

    return {
        "hourly": u["hourly"],
        "weekly": weekly,
        "monthly": monthly
    }

# ================= OTHER APIs =================
@app.get("/alerts/{user}")
def alerts(user: str):
    return {"msg": get_alert(users[user])}

@app.get("/plan/{user}")
def plan(user: str):
    return {"plan": users[user]["plans"]}

@app.get("/predict/{user}")
def prediction(user: str):
    return {"next_day": predict(users[user])}

@app.get("/blockchain/{user}")
def blockchain(user: str):
    return users[user]["blockchain"]

@app.get("/summary/{user}")
def summary(user: str):
    return users[user]["monthly_bills"]

@app.post("/budget/{user}/{amount}")
def budget(user: str, amount: int):
    users[user]["monthly_budget"] = amount
    return {"msg": "updated"}
