import streamlit as st
import math
import pandas as pd

st.set_page_config(
    page_title="Concrete Mix Design | IS 10262",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Exo 2', sans-serif; }
.stApp { background: linear-gradient(135deg, #0a1628 0%, #0f2040 50%, #0a1628 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1f35 0%, #112540 100%); border-right: 1px solid #1e3a5f; }
div[data-testid="metric-container"] { background: linear-gradient(135deg, #112540, #1a3a5c); border: 1px solid #1e4d7a; border-radius: 10px; padding: 16px 20px; }
div[data-testid="metric-container"] label { color: #5ba3d4 !important; font-size: 0.75rem !important; font-weight: 700 !important; font-family: 'Share Tech Mono', monospace !important; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #f0a500 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 1.6rem !important; }
.stButton > button { background: linear-gradient(135deg, #e8a020, #c07010); color: #0a1628; font-weight: 700; border: none; border-radius: 6px; width: 100%; }
.section-header { font-family: 'Share Tech Mono', monospace; font-size: 0.78rem; color: #0a1628; background: linear-gradient(90deg, #e8a020, #c07010); padding: 6px 14px; border-radius: 4px; margin: 16px 0 10px 0; display: inline-block; font-weight: 700; }
.result-box { background: linear-gradient(135deg, #0d1f35, #112540); border: 1px solid #1e4d7a; border-left: 4px solid #e8a020; border-radius: 8px; padding: 20px 24px; font-family: 'Share Tech Mono', monospace; font-size: 0.85rem; color: #c8dff0; line-height: 1.9; white-space: pre-wrap; }
.main-title { font-family: 'Share Tech Mono', monospace; font-size: 2rem; color: #e8a020; letter-spacing: 0.1em; }
.main-sub { font-family: 'Exo 2', sans-serif; font-size: 0.9rem; color: #5ba3d4; letter-spacing: 0.15em; text-transform: uppercase; }
.ratio-card { background: linear-gradient(135deg, #0f2a45, #1a3d5c); border: 1px solid #2a6090; border-top: 3px solid #4fc3f7; border-radius: 8px; padding: 18px 22px; text-align: center; }
.ratio-label { font-family: 'Exo 2', sans-serif; font-size: 0.72rem; color: #5ba3d4; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 700; }
.ratio-value { font-family: 'Share Tech Mono', monospace; font-size: 1.3rem; color: #4fc3f7; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)

STD_DEVIATION = {"M10":3.5,"M15":4.0,"M20":4.0,"M25":4.0,"M30":5.0,"M35":5.0,"M40":5.0,"M45":5.0,"M50":5.0}
MAX_WC = {"M10":0.60,"M15":0.60,"M20":0.55,"M25":0.50,"M30":0.50,"M35":0.45,"M40":0.45,"M45":0.40,"M50":0.40}
WATER_CONTENT = {"Very Low  (0-25 mm)":172,"Low       (25-50 mm)":180,"Medium    (50-100 mm)":186,"High      (100-150 mm)":195,"Very High (150 mm+)":202}
CA_FRACTION = {"Zone I":{0.40:0.71,0.45:0.69,0.50:0.66,0.55:0.64,0.60:0.62},"Zone II":{0.40:0.69,0.45:0.67,0.50:0.64,0.55:0.62,0.60:0.60},"Zone III":{0.40:0.67,0.45:0.65,0.50:0.62,0.55:0.60,0.60:0.58},"Zone IV":{0.40:0.65,0.45:0.63,0.50:0.60,0.55:0.58,0.60:0.56}}
MIN_CEMENT = {"Mild":300,"Moderate":300,"Severe":320,"Very Severe":340,"Extreme":360}

def interpolate_ca(zone, wc):
    tbl = CA_FRACTION[zone]
    keys = sorted(tbl.keys())
    if wc <= keys[0]: return tbl[keys[0]]
    if wc >= keys[-1]: return tbl[keys[-1]]
    for i in range(len(keys)-1):
        k1, k2 = keys[i], keys[i+1]
        if k1 <= wc <= k2:
            t = (wc-k1)/(k2-k1)
            return tbl[k1] + t*(tbl[k2]-tbl[k1])
    return tbl[keys[-1]]

def calculate_mix(grade,exposure,sg_c,sg_fa,sg_ca,abs_fa,abs_ca,zone,slump,msa_str,use_adm,water_red,use_fly,fa_pct,sg_fly):
    fck = int(grade[1:])
    steps = []
    S = STD_DEVIATION[grade]
    fck_t = fck + 1.65 * S
    steps.append(("STEP 1 - Target Mean Compressive Strength", f"fck = {fck} MPa  |  S = {S} MPa\nf'ck = {fck} + {1.65*S:.2f} = {fck_t:.2f} MPa"))
    wc_calc = round(12.25 / (1.115 ** fck_t), 3)
    wc_max = MAX_WC[grade]
    wc = min(wc_calc, wc_max)
    steps.append(("STEP 2 - Water-Cement Ratio", f"Computed W/C = {wc_calc:.3f}\nMax W/C (IS 456) = {wc_max}\nAdopted W/C = {wc:.3f}"))
    water_base = WATER_CONTENT[slump]
    msa_corr = {"10mm":3,"16mm":1.5,"20mm":0,"25mm":-1.5,"40mm":-6}
    water_msa = water_base * (1 + msa_corr.get(msa_str, 0)/100)
    water_final = water_msa * (1 - water_red/100) if use_adm else water_msa
    steps.append(("STEP 3 - Water Content", f"Base = {water_base} lt/m3\nAfter MSA correction = {water_msa:.1f} lt/m3\nAdopted = {water_final:.1f} lt/m3"))
    cement_raw = water_final / wc
    flyash_mass = cement_raw * (fa_pct/100) if use_fly else 0
    cement_final = cement_raw - flyash_mass
    if not use_fly: sg_fly = 2.2
    min_c = MIN_CEMENT[exposure]
    adopted_cement = max(cement_final, min_c)
    warn = f"Adopted {adopted_cement:.1f} kg/m3" + (" (min cement applied)" if cement_final < min_c else " - OK")
    steps.append(("STEP 4 - Cement Content", warn + (f"\nFly Ash = {flyash_mass:.1f} kg/m3" if use_fly else "")))
    vol_water = water_final/1000
    vol_cement = adopted_cement/(sg_c*1000)
    vol_flyash = flyash_mass/(sg_fly*1000) if use_fly else 0
    air = 0.02
    vol_agg = 1 - vol_water - vol_cement - vol_flyash - air
    ca_frac = interpolate_ca(zone, wc)
    if msa_str == "10mm": ca_frac -= 0.10
    elif msa_str == "40mm": ca_frac += 0.05
    ca_frac = max(0.30, min(ca_frac, 0.90))
    vol_ca = vol_agg * ca_frac
    vol_fa_agg = vol_agg * (1 - ca_frac)
    mass_ca = vol_ca * sg_ca * 1000
    mass_fa = vol_fa_agg * sg_fa * 1000
    steps.append(("STEP 5 - Aggregate Volumes", f"Vol. Agg = {vol_agg:.4f} m3\nCA Fraction = {ca_frac:.3f}\nCA = {mass_ca:.1f} kg/m3 | FA = {mass_fa:.1f} kg/m3"))
    r_fa = round(mass_fa/adopted_cement, 2)
    r_ca = round(mass_ca/adopted_cement, 2)
    r_w = round(water_final/adopted_cement, 2)
    steps.append(("STEP 6 - Mix Proportions", f"Cement : FA : CA : Water\n1 : {r_fa} : {r_ca} : {r_w}\nDesign complete - IS 10262 : 2019"))
    return {"fck_t":fck_t,"wc":wc,"water":water_final,"cement":adopted_cement,"flyash":flyash_mass,"fa":mass_fa,"ca":mass_ca,"vol_cement":vol_cement,"vol_flyash":vol_flyash,"vol_fa":vol_fa_agg,"vol_ca":vol_ca,"vol_water":vol_water,"r_fa":r_fa,"r_ca":r_ca,"r_w":r_w,"use_fly":use_fly,"steps":steps}

st.markdown('<div class="main-title">CONCRETE MIX DESIGN</div>', unsafe_allow_html=True)
st.markdown('<div class="main-sub">IS 10262 : 2019 | IS 456 : 2000 | Absolute Volume Method</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Design Inputs")
    st.markdown('<div class="section-header">1. GRADE & EXPOSURE</div>', unsafe_allow_html=True)
    grade = st.selectbox("Grade of Concrete", ["M10","M15","M20","M25","M30","M35","M40","M45","M50"], index=3)
    exposure = st.selectbox("Exposure Condition", ["Mild","Moderate","Severe","Very Severe","Extreme"])
    st.markdown('<div class="section-header">2. CEMENT</div>', unsafe_allow_html=True)
    cement_type = st.selectbox("Type of Cement", ["OPC 33","OPC 43","OPC 53","PPC","PSC","SRC"], index=2)
    sg_c = st.number_input("Sp. Gravity of Cement", value=3.15, step=0.01, format="%.2f")
    st.markdown('<div class="section-header">3. AGGREGATE</div>', unsafe_allow_html=True)
    msa_str = st.selectbox("Max Size of Aggregate", ["10mm","16mm","20mm","25mm","40mm"], index=2)
    zone = st.selectbox("Fine Aggregate Zone (IS 383)", ["Zone I","Zone II","Zone III","Zone IV"], index=1)
    sg_fa = st.number_input("Sp. Gravity - Fine Agg.", value=2.65, step=0.01, format="%.2f")
    sg_ca = st.number_input("Sp. Gravity - Coarse Agg.", value=2.70, step=0.01, format="%.2f")
    abs_fa = st.number_input("Water Absorption - FA (%)", value=1.0, step=0.1, format="%.1f")
    abs_ca = st.number_input("Water Absorption - CA (%)", value=0.5, step=0.1, format="%.1f")
    st.markdown('<div class="section-header">4. WORKABILITY</div>', unsafe_allow_html=True)
    slump = st.selectbox("Required Workability", list(WATER_CONTENT.keys()), index=2)
    st.markdown('<div class="section-header">5. ADMIXTURES</div>', unsafe_allow_html=True)
    use_adm = st.checkbox("Use Plasticizer / Superplasticizer")
    water_red = st.slider("Water Reduction (%)", 5, 35, 20) if use_adm else 0.0
    use_fly = st.checkbox("Use Fly Ash (IS 1344)")
    fa_pct = 0.0
    sg_fly = 2.20
    if use_fly:
        fa_pct = st.slider("Fly Ash Replacement (%)", 5, 35, 20)
        sg_fly = st.number_input("Sp. Gravity - Fly Ash", value=2.20, step=0.01, format="%.2f")
    st.markdown("---")
    calc = st.button("CALCULATE MIX DESIGN")

if calc:
    res = calculate_mix(grade,exposure,sg_c,sg_fa,sg_ca,abs_fa/100,abs_ca/100,zone,slump,msa_str,use_adm,water_red,use_fly,fa_pct,sg_fly)
    st.markdown("#### Key Design Parameters")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("W/C Ratio", f"{res['wc']:.3f}")
    c2.metric("Water Content", f"{res['water']:.1f} lt/m3")
    c3.metric("Cement Content", f"{res['cement']:.1f} kg/m3")
    c4.metric("Target f'ck", f"{res['fck_t']:.2f} MPa")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Mix Proportion - Cement : FA : CA : Water")
    r1,r2,r3,r4 = st.columns(4)
    for col,label,val,color in [(r1,"CEMENT","1.000","#e8a020"),(r2,"FINE AGG",str(res['r_fa']),"#4fc3f7"),(r3,"COARSE AGG",str(res['r_ca']),"#43d18a"),(r4,"WATER",str(res['r_w']),"#ef9a9a")]:
        col.markdown(f'<div class="ratio-card"><div class="ratio-label">{label}</div><div class="ratio-value" style="color:{color}">{val}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Quantity per m3 of Concrete")
    rows = [{"Material":"Cement","Quantity (kg/m3)":round(res['cement'],2),"Volume (m3)":round(res['vol_cement'],4),"Ratio":1.0}]
    if res['use_fly']:
        rows.append({"Material":"Fly Ash","Quantity (kg/m3)":round(res['flyash'],2),"Volume (m3)":round(res['vol_flyash'],4),"Ratio":round(res['flyash']/res['cement'],3)})
    rows += [{"Material":"Fine Aggregate","Quantity (kg/m3)":round(res['fa'],2),"Volume (m3)":round(res['vol_fa'],4),"Ratio":res['r_fa']},{"Material":"Coarse Aggregate","Quantity (kg/m3)":round(res['ca'],2),"Volume (m3)":round(res['vol_ca'],4),"Ratio":res['r_ca']},{"Material":"Water","Quantity (kg/m3)":round(res['water'],2),"Volume (m3)":round(res['vol_water'],4),"Ratio":res['r_w']}]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Design Steps - IS 10262 : 2019")
    for title, body in res['steps']:
        with st.expander(f"{title}"):
            st.code(body, language=None)
    st.success("Mix design completed successfully as per IS 10262 : 2019 & IS 456 : 2000")
else:
    st.info("Fill in the inputs on the left panel and click CALCULATE MIX DESIGN to get results.")