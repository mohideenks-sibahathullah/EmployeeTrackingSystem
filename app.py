import streamlit as st
import boto3
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Enterprise Employee Tracking", page_icon="🏢", layout="wide")

# AWS Constants
REGION = "ap-south-1"
PROFILE_TABLE = "EmployeeProfile"
LOGS_TABLE = "AttendanceLogs"
COLLECTION_ID = "EmployeeFaces"

# Initialize AWS Clients
rek_client = boto3.client('rekognition', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
profile_db = dynamodb.Table(PROFILE_TABLE)
logs_db = dynamodb.Table(LOGS_TABLE)

# --- NAVIGATION ---
page = st.sidebar.radio("Main Menu", ["📸 Mark Attendance", "👤 HR Onboarding"])

# --- PAGE 1: HR ONBOARDING (REGISTRATION) ---
if page == "👤 HR Onboarding":
    st.title("Employee Registration Portal")
    st.info("Fill in the employee details and capture their face for biometric enrollment.")
    
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            emp_id = st.text_input("Employee ID")
            f_name = st.text_input("First Name")
            l_name = st.text_input("Last Name")
        with c2:
            city = st.text_input("City")
            state = st.text_input("State")
            pin = st.text_input("Pin Code")
        
        photo = st.camera_input("Enrollment Photo")
        submit = st.form_submit_button("Register New Employee")

    if submit and emp_id and photo:
        try:
            # 1. Store in EmployeeProfile
            profile_db.put_item(Item={
                'EmployeeId': emp_id,
                'FirstName': f_name,
                'LastName': l_name,
                'City': city,
                'State': state,
                'Pincode': pin
            })
            # 2. Index face in Collection
            rek_client.index_faces(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': photo.getvalue()},
                ExternalImageId=emp_id,
                MaxFaces=1
            )
            st.success(f"✅ Success! {f_name} is now registered.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- PAGE 2: ATTENDANCE (AUTOMATED) ---
elif page == "📸 Mark Attendance":
    st.title("Smart Attendance Terminal")
    st.write("Just look at the camera. The system will recognize you and log your time.")
    
    img = st.camera_input("Scan Face")
    if img:
        try:
            # 1. Search Face
            search = rek_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': img.getvalue()},
                MaxFaces=1,
                FaceMatchThreshold=90
            )
            
            if not search.get('FaceMatches'):
                st.error("❌ Identity Not Found. Please contact HR.")
            else:
                eid = search['FaceMatches'][0]['Face']['ExternalImageId']
                
                # 2. Get Name from Profile Table
                person = profile_db.get_item(Key={'EmployeeId': eid}).get('Item', {})
                name = person.get('FirstName', 'Employee')
                
                # 3. Check Today's Logs for Login/Logout
                now = datetime.now()
                today = now.strftime('%Y-%m-%d')
                
                history = logs_db.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('EmployeeId').eq(eid)
                )
                today_entries = [i for i in history['Items'] if i['Timestamp'].startswith(today)]
                
                action = "LOGIN" if len(today_entries) == 0 else "LOGOUT"
                
                if len(today_entries) >= 2:
                    st.warning(f"Hello {name}, you have already finished your shift today.")
                else:
                    logs_db.put_item(Item={
                        'EmployeeId': eid,
                        'Timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
                        'ActionType': action
                    })
                    st.success(f"✅ {action} Successful: Hello {name} from {person.get('City')}!")
                    st.balloons()
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- DASHBOARD ---
st.divider()
if st.button("📊 View Live Attendance Records"):
    recs = logs_db.scan().get('Items', [])
    st.table(sorted(recs, key=lambda x: x['Timestamp'], reverse=True))
