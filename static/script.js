document.addEventListener('DOMContentLoaded', function () {
    // Funcionalidad de Checklist
    const numeroCocheInput = document.getElementById('numero_coche');
    const lastUpdateElement = document.getElementById('lastUpdate');
    const mensaje = document.getElementById('mensaje');
    
    if (numeroCocheInput) {
        numeroCocheInput.addEventListener('change', function () {
            const numeroCoche = this.value.trim();
            if (numeroCoche) {
                console.log('Buscando datos para el coche con número:', numeroCoche);
                fetch(`/get_car_details/${numeroCoche}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log('Datos obtenidos:', data);
                        if (data.error) {
                            mensaje.textContent = "Coche no encontrado.";
                            return;
                        }
                        // Rellenamos campos del checklist
                        const campos = ['kilometraje', 'luces', 'antena', 'espejo_derecho', 'espejo_izquierdo', 'cristales', 'emblema', 
                                        'llantas', 'tapon_gasolina', 'carroceria_sin_golpes', 'claxon', 'instrumentos_tablero', 
                                        'clima', 'limpiadores', 'bocinas', 'espejo_retrovisor', 'cinturones', 'botones_interiores', 
                                        'manijas_interiores', 'tapetes', 'vestiduras', 'gato', 'maneral_gato', 'llave_ruedas', 
                                        'refacciones', 'herramientas', 'extintor', 'aceite', 'anticongelante', 'liquido_frenos', 
                                        'tarjeta_circulacion', 'papeles_seguro', 'licencia_vigente'];
                        campos.forEach(campo => {
                            const radioSi = document.getElementById(`${campo}_si`);
                            const radioNo = document.getElementById(`${campo}_no`);
                            if (radioSi && radioNo) {
                                if (data[campo]) {
                                    radioSi.checked = true;
                                } else {
                                    radioNo.checked = true;
                                }
                            }
                            const inputField = document.getElementById(campo);
                            if (inputField && data[campo]) {
                                inputField.value = data[campo];
                            }
                        });
                        // Actualizar última actualización
                        if (lastUpdateElement && data.ultima_actualizacion) {
                            lastUpdateElement.textContent = `Última actualización: ${data.ultima_actualizacion}`;
                        }
                        mensaje.textContent = `Datos cargados para el coche con matrícula: ${numeroCoche}`;
                    })
                    .catch(error => {
                        console.error('Error al obtener los detalles del coche:', error);
                        mensaje.textContent = "Error al cargar los detalles del coche.";
                    });
            }
        });
    }

    // Funcionalidad de la cámara y escaneo QR
    const video = document.getElementById('video');
    const canvas = document.createElement('canvas');
    const escanearBtn = document.getElementById('escanear-btn');
    const qrDataInput = document.getElementById('qr_data');
    const nombreTecnicoInput = document.getElementById('nombre_persona');
    const ultimoMantenimientoInput = document.getElementById('ultimo_mantenimiento');
    
    // Acceder a la cámara
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(err => {
            console.error("Error al acceder a la cámara: ", err);
        });

    escanearBtn.addEventListener('click', () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);

        const imageData = canvas.toDataURL('image/png').replace(/^data:image\/(png|jpg);base64,/, '');
        
        fetch('/escaneo_qr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                mensaje.textContent = "QR detectado: " + data.qr_data;
                qrDataInput.value = data.qr_data;
                console.log("QR Data Capturado:", data.qr_data);

                // Verificar si el QR ya existe
                fetch('/verificar_qr', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ qr_data: data.qr_data })
                })
                .then(response => response.json())
                .then(qrInfo => {
                    if (qrInfo.exists) {
                        nombreTecnicoInput.value = qrInfo.nombre_tecnico;
                        ultimoMantenimientoInput.value = qrInfo.ultimo_mantenimiento;
                        mensaje.textContent += " (Datos existentes cargados)";
                    } else {
                        nombreTecnicoInput.value = '';
                        ultimoMantenimientoInput.value = '';
                        mensaje.textContent += " (Nuevo QR, ingrese los datos)";
                    }
                })
                .catch(err => {
                    console.error('Error al verificar el QR: ', err);
                });
            } else {
                mensaje.textContent = "No se detectó ningún QR.";
            }
        })
        .catch(err => {
            console.error('Error al procesar la imagen: ', err);
        });
    });
});
