import csv
import subprocess
from math import cos, sin, radians, sqrt
from pathlib import Path

from flask import Flask, send_file, request, jsonify


BASE_DIR = Path(__file__).resolve().parent

grafo_archive = BASE_DIR / "csv" / "grafo.csv"
nodo_archive = BASE_DIR / "csv" / "nodos.csv"
Evento_archive = BASE_DIR / "Eventos.csv"
programa_archive = BASE_DIR / "programa"

app = Flask(__name__)

coords = {}
ids_grafo = set()
argumentos = []


def calcularCoord(latitud, longitud, altitud):
    R = 6371000

    latitud = radians(latitud)
    longitud = radians(longitud)

    x = (R + altitud) * cos(latitud) * cos(longitud)
    y = (R + altitud) * cos(latitud) * sin(longitud)
    z = (R + altitud) * sin(latitud)

    return [x, y, z]


with open(nodo_archive, "r", encoding="utf-8") as archive:
    lector = csv.reader(archive)
    next(lector)

    for fila in lector:
        id_nodo = int(fila[0])
        latitud = float(fila[1])
        longitud = float(fila[2])
        altitud = float(fila[3])

        coords[id_nodo] = calcularCoord(
            latitud,
            longitud,
            altitud
        )


with open(grafo_archive, "r", encoding="utf-8") as archive:
    lector = csv.reader(archive)
    next(lector)

    for fila in lector:
        origen = int(fila[0])
        destino = int(fila[1])

        x1, y1, z1 = coords[origen]
        x2, y2, z2 = coords[destino]

        distancia = sqrt(
            (x2 - x1) ** 2 +
            (y2 - y1) ** 2 +
            (z2 - z1) ** 2
        )

        argumentos.append(
            f"{origen},{destino},{distancia}"
        )

        ids_grafo.add(origen)
        ids_grafo.add(destino)


def obtenerRuta():
    ruta = []

    with open(Evento_archive, "r", encoding="utf-8") as archive:
        lector = csv.reader(archive)
        next(lector)

        for fila in lector:
            if len(fila) < 3 or fila[0] != "PACKAGESEND":
                continue

            origen, destino = fila[2].split("-", 1)

            origen = int(origen)
            destino = int(destino)

            if not ruta:
                ruta.append(origen)

            if destino != -1:
                ruta.append(destino)

    return ruta


@app.route("/")
def mostrar_mapa():
    return send_file(BASE_DIR / "mapa.html")


@app.route("/seleccion", methods=["POST"])
def recibir_seleccion():
    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return jsonify({"error": "Datos no válidos"}), 400

    try:
        origen = int(datos["origen"])
        destino = int(datos["destino"])
    except (KeyError, ValueError, TypeError):
        return jsonify({
            "error": "El origen y el destino deben ser IDs enteros."
        }), 400

    if origen not in ids_grafo or destino not in ids_grafo:
        return jsonify({
            "error": "Uno de los nodos no pertenece al grafo."
        }), 400

    if not programa_archive.is_file():
        return jsonify({
            "error": "No se encontró el ejecutable programa."
        }), 500

    try:
        resultado = subprocess.run(
            [
                str(programa_archive),
                str(origen),
                str(destino)
            ] + argumentos,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )
    except subprocess.TimeoutExpired:
        return jsonify({
            "error": "El cálculo de la ruta superó el tiempo límite."
        }), 500
    except OSError as error:
        return jsonify({
            "error": f"No se pudo ejecutar C++: {error}"
        }), 500

    if resultado.returncode != 0:
        print("Error de C++:", resultado.stderr)

        return jsonify({
            "error": "El programa C++ no pudo calcular la ruta.",
            "detalle": resultado.stderr or resultado.stdout
        }), 500

    ruta = obtenerRuta()

    distancia_total = 0

    for i in range(len(ruta) - 1):
        nodo_origen = ruta[i]
        nodo_destino = ruta[i + 1]

        x1, y1, z1 = coords[nodo_origen]
        x2, y2, z2 = coords[nodo_destino]

        distancia_total += sqrt(
            (x2 - x1) ** 2 +
            (y2 - y1) ** 2 +
            (z2 - z1) ** 2
        )

    if not ruta or ruta[0] != origen or ruta[-1] != destino:
        return jsonify({
            "error": "No se encontró una ruta entre esos dos nodos."
        }), 422

    print("Origen recibido:", origen)
    print("Destino recibido:", destino)
    print("Ruta calculada:", ruta)
    print("Cantidad de nodos en la ruta:", len(ruta))

    return jsonify({
        "estado": "ok",
        "origen": origen,
        "destino": destino,
        "ruta": ruta,
        "distancia_metros": round(distancia_total, 1),
        "distancia_km": round(distancia_total / 1000, 2),
        "cantidad_nodos": len(ruta)
    })


if __name__ == "__main__":
    app.run(debug=True)