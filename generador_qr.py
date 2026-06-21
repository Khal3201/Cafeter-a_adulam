import qrcode

url = "https://iplogger.com/2Lx2M6"

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
img.save("qr.png")

print("QR generado y guardado como qr_produccion.png")
print("Apunta a:", url)