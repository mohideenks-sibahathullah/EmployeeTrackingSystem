import boto3

# CONFIGURATION: Update these to match your setup exactly
BUCKET_NAME = "attendance-faces-mohideen"
COLLECTION_ID = "StudentAttendanceCollection"
REGION = "ap-south-1"

# Initialize Rekognition client
rek_client = boto3.client('rekognition', region_name=REGION)

def process_attendance(photo_name):
    print(f"\n--- Processing Attendance for: {photo_name} ---")

    # 1. VALIDATION: Check for Face Mask (PPE Detection)
    ppe_response = rek_client.detect_protective_equipment(
        Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': photo_name}},
        SummarizationAttributes={'RequiredEquipmentTypes': ['FACE_COVER'], 'MinConfidence': 80}
    )
    
    for person in ppe_response['Persons']:
        for part in person['BodyParts']:
            if part['Name'] == 'FACE':
                for item in part['EquipmentDetections']:
                    if item['Type'] == 'FACE_COVER' and item['CoversBodyPart']['Value']:
                        return "FAILED: Please remove your face mask to mark attendance."

    # 2. VALIDATION: Quality & Spoof Check (using DetectFaces)
    face_detail = rek_client.detect_faces(
        Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': photo_name}},
        Attributes=['ALL']
    )
    
    if not face_detail['FaceDetails']:
        return "FAILED: No face detected. Please face the camera clearly."
        
    quality = face_detail['FaceDetails'][0]['Quality']
    # If image is very blurry (Sharpness < 60), it's likely a photo-of-a-photo or billboard
    if quality['Sharpness'] < 60:
        return "FAILED: Spoof detected or low quality. Please use a live camera."

    # 3. IDENTIFICATION: Match against the Student Collection
    try:
        match_response = rek_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': photo_name}},
            MaxFaces=1,
            FaceMatchThreshold=90
        )
        
        if match_response['FaceMatches']:
            student_id = match_response['FaceMatches'][0]['Face']['ExternalImageId']
            confidence = match_response['FaceMatches'][0]['Similarity']
            return f"SUCCESS: Attendance marked for {student_id} (Confidence: {confidence:.2f}%)"
        else:
            return "FAILED: Identity not recognized. Please register first."
            
    except Exception as e:
        return f"ERROR: {str(e)}"

# TEST: Ensure 'test_me.jpg' exists in your S3 bucket before running
if __name__ == "__main__":
    result = process_attendance("test_me.jpg")
    print(result)
