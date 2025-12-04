from google.cloud import vision

client = vision.ImageAnnotatorClient()

with open("student_work/week_6/DesmondLai_Week6.jpg", "rb") as f:
    content = f.read()

image = vision.Image(content=content)
response = client.document_text_detection(image=image)

print(response.full_text_annotation.text)
