import streamlit as st
import boto3
from PIL import Image
import io

# AWS Configuration
REGION = "ap-south-1"
COLLECTION_ID = "EmployeeFaces"

# Initialize Rekognition Client
rekognition = boto3.client('rekognition', region_name=REGION)

st.set_page_config(page_title="Employee Registration", page_icon="👤")

st.title("👤 Self-Registration Portal")
st.markdown("---")
st.write("Existing employees: Enter your ID and capture your photo to register.")

# Step 1: Input Employee ID
emp_id = st.text_input("Enter your unique Employee ID:")

if emp_id:
    # Step 2: Access Camera
    img_file = st.camera_input("Capture your registration photo")

    if img_file:
        # Convert image to bytes for AWS
        image = Image.open(img_file)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        if st.button("Complete Registration"):
            with st.spinner("Registering your face in the system..."):
                try:
                    # Index the face into the collection
                    response = rekognition.index_faces(
                        CollectionId=COLLECTION_ID,
                        Image={'Bytes': img_bytes},
                        ExternalImageId=emp_id,
                        DetectionAttributes=['ALL']
                    )
                    
                    if response['FaceRecords']:
                        st.success(f"✅ Success! {emp_id} is now registered.")
                        st.balloons()
                        st.info("You can now use the mobile terminal for attendance.")
                    else:
                        st.error("❌ Face not detected clearly. Please ensure your face is visible and well-lit.")
                        
                except Exception as e:
                    st.error(f"System Error: {str(e)}")
