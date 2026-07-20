/**
 * Dev-only preview fixtures — the exact Pune Rural District demo scenario.
 * Active ONLY when VITE_PREVIEW=1 (never in production builds). Lets anyone
 * run the UI without Firebase credentials or seeded data:
 *   VITE_PREVIEW=1 npm run dev   →  /?role=admin  or  /?role=operator
 */

const days = (n) => {
  const out = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    out.push(d.toISOString().slice(0, 10).replace(/-/g, ""));
  }
  return out;
};

export const CENTRES = [
  { id: "phc_mulshi", name: "PHC Mulshi", type: "PHC", district_id: "pune_rural", status: "critical", performance_score: 55, location: { block: "Mulshi Taluka" }, footfall_today: 82, beds_total: 12, beds_occupied: 8, beds_available: 4 },
  { id: "phc_haveli", name: "PHC Haveli", type: "PHC", district_id: "pune_rural", status: "critical", performance_score: 58, location: { block: "Haveli Taluka" }, footfall_today: 74, beds_total: 10, beds_occupied: 4, beds_available: 6 },
  { id: "phc_ambegaon", name: "PHC Ambegaon", type: "PHC", district_id: "pune_rural", status: "warning", performance_score: 72, location: { block: "Ambegaon Taluka" }, footfall_today: 70, beds_total: 10, beds_occupied: 6, beds_available: 4 },
  { id: "chc_pune_rural", name: "Pune Rural CHC", type: "CHC", district_id: "pune_rural", status: "operational", performance_score: 91, location: { block: "Community Health Centre" }, footfall_today: 140, beds_total: 60, beds_occupied: 45, beds_available: 15 },
  { id: "phc_velhe", name: "PHC Velhe", type: "PHC", district_id: "pune_rural", status: "under_resourced", performance_score: 38, location: { block: "Velhe Taluka" }, footfall_today: 40, beds_total: 10, beds_occupied: 2, beds_available: 8 },
  { id: "phc_bhor", name: "PHC Bhor", type: "PHC", district_id: "pune_rural", status: "operational", performance_score: 88, location: { block: "Bhor Taluka" }, footfall_today: 61, beds_total: 8, beds_occupied: 5, beds_available: 3 },
];

export const ALERTS = [
  { id: "a1", district_id: "pune_rural", centre_id: "phc_mulshi", centre_name: "PHC Mulshi", type: "STOCKOUT_CRITICAL", severity: "critical", medicine_name: "Paracetamol 500mg", days_remaining: 3, message: "Paracetamol 500mg will stock out in 3 days — reorder now", resolved: false },
  { id: "a2", district_id: "pune_rural", centre_id: "phc_haveli", centre_name: "PHC Haveli", type: "STOCKOUT_CRITICAL", severity: "critical", medicine_name: "ORS Sachets", days_remaining: 2, message: "ORS Sachets will stock out in 2 days — reorder now", resolved: false },
  { id: "a3", district_id: "pune_rural", centre_id: "phc_ambegaon", centre_name: "PHC Ambegaon", type: "STOCKOUT_WARNING", severity: "high", medicine_name: "Iron + Folic Acid", days_remaining: 5, message: "Iron + Folic Acid low: 5 days remaining", resolved: false },
  { id: "a4", district_id: "pune_rural", centre_id: "phc_velhe", centre_name: "PHC Velhe", type: "UNDERPERFORMANCE", severity: "medium", message: "PHC Velhe flagged: score 38/100", resolved: false },
  { id: "a5", district_id: "pune_rural", centre_id: "phc_velhe", centre_name: "PHC Velhe", type: "DATA_INTEGRITY", severity: "medium", check_type: "CONSUMPTION_WITHOUT_PATIENTS", medicine_name: "Paracetamol 500mg", message: "Paracetamol 500mg leaving at 4.8 units per patient — far above normal; verify dispensing vs diversion", resolved: false },
  { id: "a6", district_id: "pune_rural", centre_id: "phc_velhe", centre_name: "PHC Velhe", type: "CITIZEN_DISPUTE", severity: "high", check_type: "DOCTOR_ABSENCE", message: "4 citizens report no doctor present today, but the centre reports a doctor on duty", resolved: false },
];

export const RECOMMENDATIONS = [
  { id: "r1", district_id: "pune_rural", type: "REDISTRIBUTION", from_centre: "Pune Rural CHC", from_centre_id: "chc_pune_rural", to_centre: "PHC Mulshi", to_centre_id: "phc_mulshi", medicine: "Paracetamol 500mg", medicine_id: "paracetamol", quantity: 200, urgency: "critical", status: "pending", gemini_message: "Move 200 Paracetamol tablets from Pune Rural CHC to PHC Mulshi — 3 days of stock left." },
  { id: "r2", district_id: "pune_rural", type: "REDISTRIBUTION", from_centre: "Pune Rural CHC", from_centre_id: "chc_pune_rural", to_centre: "PHC Haveli", to_centre_id: "phc_haveli", medicine: "ORS Sachets", medicine_id: "ors", quantity: 150, urgency: "critical", status: "pending", gemini_message: "Move 150 ORS sachets from Pune Rural CHC to PHC Haveli — 2 days left." },
  { id: "r3", district_id: "pune_rural", type: "REDISTRIBUTION", from_centre: "Pune Rural CHC", from_centre_id: "chc_pune_rural", to_centre: "PHC Ambegaon", to_centre_id: "phc_ambegaon", medicine: "Iron + Folic Acid", medicine_id: "ifa", quantity: 300, urgency: "high", status: "disputed", received_qty: 210, shortfall: 90, gemini_message: "" },
];

const STOCK = {
  phc_mulshi: [
    { id: "paracetamol", medicine_name: "Paracetamol 500mg", unit: "tablets", current_stock: 120, days_remaining: 3 },
    { id: "ors", medicine_name: "ORS Sachets", unit: "sachets", current_stock: 340, days_remaining: 14 },
    { id: "ifa", medicine_name: "Iron + Folic Acid", unit: "tablets", current_stock: 450, days_remaining: 8 },
    { id: "amoxicillin", medicine_name: "Amoxicillin 250mg", unit: "tablets", current_stock: 300, days_remaining: 12 },
    { id: "metformin", medicine_name: "Metformin 500mg", unit: "tablets", current_stock: 500, days_remaining: 18 },
  ],
  phc_velhe: [
    { id: "paracetamol", medicine_name: "Paracetamol 500mg", unit: "tablets", current_stock: 300, days_remaining: 10 },
    { id: "ors", medicine_name: "ORS Sachets", unit: "sachets", current_stock: 220, days_remaining: 9 },
    { id: "ifa", medicine_name: "Iron + Folic Acid", unit: "tablets", current_stock: 340, days_remaining: 11 },
  ],
};
STOCK.phc_haveli = STOCK.phc_mulshi.map((m) =>
  m.id === "ors" ? { ...m, current_stock: 90, days_remaining: 2 } : { ...m, days_remaining: 12 }
);
STOCK.default = STOCK.phc_velhe;

const last7 = days(7);
const last30 = days(30);
const ATTENDANCE = last7.map((date, i) => ({
  id: date, date,
  doctors_present: [1, 2, 1, 2, 1, 1, 2][i], doctors_total: 2,
  nurses_present: [2, 2, 1, 2, 2, 1, 2][i], nurses_total: 3,
  attendance_rate: [0.6, 0.8, 0.4, 0.8, 0.6, 0.4, 0.8][i],
}));
const FOOTFALL = last30.map((date, i) => ({
  id: date, date, count: Math.round(80 - i * 1.2 + (i % 5) * 4), opd: 0, ipd: 0,
}));

export function previewCollection(path) {
  if (path === "centres") return CENTRES;
  if (path === "alerts") return ALERTS;
  if (path === "recommendations") return RECOMMENDATIONS;
  const m = path.match(/^centres\/([^/]+)\/(stock|attendance|footfall)$/);
  if (m) {
    if (m[2] === "stock") return STOCK[m[1]] || STOCK.default;
    if (m[2] === "attendance") return ATTENDANCE;
    if (m[2] === "footfall") return FOOTFALL;
  }
  return [];
}

export function previewDoc(path) {
  const centre = CENTRES.find((c) => path === `centres/${c.id}`);
  if (centre) return centre;
  const beds = path.match(/^centres\/([^/]+)\/beds\/current$/);
  if (beds) {
    const c = CENTRES.find((x) => x.id === beds[1]);
    return c ? { id: "current", total: c.beds_total, occupied: c.beds_occupied, available: c.beds_available } : null;
  }
  if (/\/tests\/current$/.test(path)) {
    const velhe = path.includes("phc_velhe");
    return { id: "current", malaria: !velhe, tb: true, pregnancy: true, diabetes: true, hiv: true };
  }
  return null;
}

export const PREVIEW_API = {
  outbreaks: [
    { signal: "ors", indication: "diarrhoeal illness", centres: ["PHC Mulshi", "PHC Haveli"], centre_count: 2, peak_ratio: 2.1, severity: "medium" },
  ],
  impact: {
    stockouts_flagged_early: 3,
    avg_lead_time_days: 3.3,
    units_redistributed: 350,
    patients_protected: 900,
    rupees_saved: 340,
  },
  publicCentre: {
    name: "PHC Mulshi",
    type: "PHC",
    block: "Mulshi Taluka",
    doctor_present: true,
    beds: { available: 4, total: 12 },
    medicines: [
      { id: "paracetamol", name: "Paracetamol 500mg", status: "low" },
      { id: "ors", name: "ORS Sachets", status: "available" },
      { id: "ifa", name: "Iron + Folic Acid", status: "available" },
      { id: "amoxicillin", name: "Amoxicillin 250mg", status: "available" },
      { id: "metformin", name: "Metformin 500mg", status: "available" },
    ],
    tests: { malaria: true, tb: true, pregnancy: true },
  },
  voice: {
    transcript: "पॅरासिटामॉल एकशे वीस, ओआरएस पंचेचाळीस",
    items: [
      { medicine_id: "paracetamol", medicine_name: "Paracetamol 500mg", unit: "tablets", proposed_stock: 120, confidence: "high" },
      { medicine_id: "ors", medicine_name: "ORS Sachets", unit: "sachets", proposed_stock: 45, confidence: "high" },
    ],
    unmatched: [],
  },
  briefing: {
    en: "Two centres face critical medicine stock-outs within 3 days. PHC Mulshi needs Paracetamol and PHC Haveli needs ORS urgently. A transfer from Pune Rural CHC is recommended for both.",
    hi: "दो केंद्रों में 3 दिनों के भीतर गंभीर दवा समाप्ति का खतरा है। PHC मुळशी को पैरासिटामोल और PHC हवेली को ORS की तत्काल आवश्यकता है। दोनों के लिए पुणे ग्रामीण CHC से स्थानांतरण की सिफारिश की जाती है।",
    mr: "दोन केंद्रांमध्ये 3 दिवसांत गंभीर औषध तुटवड्याचा धोका आहे. PHC मुळशीला पॅरासिटामॉल आणि PHC हवेलीला ORS ची तातडीने गरज आहे. दोन्हींसाठी पुणे ग्रामीण CHC मधून हस्तांतरणाची शिफारस केली जाते.",
  },
  explanation: {
    en: "PHC Velhe scored 38/100: doctor attendance averaged 52% over 14 days, patient footfall is 49% below the district average, and the malaria test is unavailable. Recommend a district health officer visit and a staffing review.",
    hi: "PHC वेल्हे को 38/100 अंक मिले: 14 दिनों में डॉक्टर उपस्थिति औसतन 52% रही, मरीज़ों की संख्या जिला औसत से 49% कम है, और मलेरिया जाँच उपलब्ध नहीं है। जिला स्वास्थ्य अधिकारी के दौरे और स्टाफ समीक्षा की सिफारिश की जाती है।",
    mr: "PHC वेल्हेला 38/100 गुण मिळाले: 14 दिवसांत डॉक्टर उपस्थिती सरासरी 52% होती, रुग्णसंख्या जिल्हा सरासरीपेक्षा 49% कमी आहे, आणि मलेरिया तपासणी उपलब्ध नाही. जिल्हा आरोग्य अधिकाऱ्यांची भेट आणि कर्मचारी आढाव्याची शिफारस केली जाते.",
  },
};
