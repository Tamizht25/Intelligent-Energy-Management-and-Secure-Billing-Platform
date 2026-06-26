const API = "http://127.0.0.1:8000";
let user = "";

let liveChart;

// LOGIN
async function login(){
  const u = document.getElementById("username").value;
  const p = document.getElementById("password").value;

  let res = await fetch(`${API}/login?user=${u}&password=${p}`, {method:"POST"});
  if(res.status !== 200){
    alert("Login failed");
    return;
  }

  user = u;
  loginPage.classList.add("hidden");
  app.classList.remove("hidden");

  init();
}

// NAV
function showPage(id){
  document.querySelectorAll(".page").forEach(p=>p.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
}

// INIT LOOP
function init(){
  setInterval(loop,1000);
}

// LOOP
async function loop(){
  await fetch(`${API}/step/${user}`);
  loadDashboard();
  loadAppliances();
  loadAnalytics();
  loadBlockchain();
  loadPlan();
  loadSummary();
  loadPrediction();
  loadAlerts();
}

// DASHBOARD
async function loadDashboard(){
  let r = await fetch(`${API}/status/${user}`);
  let d = await r.json();

  power.innerText = d.power;
  current.innerText = d.current;
  energy.innerText = d.energy;
  hour.innerText = d.hour;
}

// APPLIANCES
async function loadAppliances(){
  let r = await fetch(`${API}/status/${user}`);
  let d = await r.json();

  let html="";
  for(let k in d.appliances){
    html += `<button class="appliance-btn ${d.appliances[k]?"active":""}" onclick="toggle('${k}')">
    ${k} (${d.appliances[k]?"ON":"OFF"})
    </button>`;
  }
  applianceList.innerHTML = html;
}

async function toggle(d){
  await fetch(`${API}/toggle/${user}/${d}`);
}

// ADD
async function addAppliance(){
  let n=name.value;
  let p=powerInput.value;
  let c=count.value;

  await fetch(`${API}/add/${user}?name=${n}&power=${p}&count=${c}`,{method:"POST"});
}

// ANALYTICS
async function loadAnalytics(){
  let r = await fetch(`${API}/analytics/${user}`);
  let d = await r.json();

  draw("hourlyChart",d.hourly);

  drawBar("weeklyChart",d.weekly,"Week");
  drawBar("monthlyChart",d.monthly,"Month");
}

function draw(id,data){
  let ctx=document.getElementById(id);
  if(!ctx) return;

  if(ctx.chart) ctx.chart.destroy();

  ctx.chart=new Chart(ctx,{
    type:"line",
    data:{labels:data.map((_,i)=>i+1),
    datasets:[{data:data}]}
  });
}

function drawBar(id,data,type){
  let ctx=document.getElementById(id);

  let labels=data.map((_,i)=>
    type=="Week"?"Week "+(i+1):
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][i]
  );

  if(ctx.chart) ctx.chart.destroy();

  ctx.chart=new Chart(ctx,{
    type:"bar",
    data:{labels:labels,datasets:[{data:data}]}
  });
}

// BLOCKCHAIN
async function loadBlockchain(){
  let r=await fetch(`${API}/blockchain/${user}`);
  let d=await r.json();

  chain.innerHTML=d.map(b=>`
    <div class="card">
    <p>${b.date}</p>
    <p>${b.energy} kWh</p>
    <p>₹${b.bill}</p>
    </div>
  `).join("");
}

// PLAN
async function loadPlan(){
  let r=await fetch(`${API}/plan/${user}`);
  let d=await r.json();

  planBox.innerHTML=d.plan.map(p=>`<p>${p}</p>`).join("");
}

// SUMMARY
async function loadSummary(){
  let r=await fetch(`${API}/summary/${user}`);
  let d=await r.json();

  summary.innerHTML=d.map(m=>`
    <div class="card">
    <p>Month ${m.month}</p>
    <p>Expected: ₹${m.expected}</p>
    <p>Actual: ₹${m.actual}</p>
    </div>
  `).join("");
}

// BUDGET
async function setBudget(){
  let val=budgetInput.value;
  await fetch(`${API}/budget/${user}/${val}`,{method:"POST"});
}

// ALERT
async function loadAlerts(){
  let r=await fetch(`${API}/alerts/${user}`);
  let d=await r.json();
  alerts.innerText=d.msg;
}

// PREDICT
async function loadPrediction(){
  let r=await fetch(`${API}/predict/${user}`);
  let d=await r.json();
  prediction.innerText="Next Day: "+d.next_day+" kWh";
}
