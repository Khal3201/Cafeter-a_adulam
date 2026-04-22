import qrcode

url = "http://192.168.1.72:5000/"

# Generar el QR
qr = qrcode.QRCode(
    version=4,  
    error_correction=qrcode.constants.ERROR_CORRECT_H, 
    box_size=20,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

# Crear la imagen
img = qr.make_image(fill_color="black", back_color="white")

# Guardar la imagen
img.save("qr_local.png")

print("QR generado y guardado como qr_local.png")