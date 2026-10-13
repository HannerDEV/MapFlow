import csv
import folium
from folium import plugins
from math import cos, sin, radians, sqrt
import subprocess

grafo_archive = "./csv/grafo.csv"
nodo_archive = "./csv/nodos.csv"
direccion_archive = "./csv/direccion.csv"
Evento_archive = "./Eventos.csv"

conexiones = []
nodos = []
distancias = []

coords = {}


with open(grafo_archive, "r") as archive:
    lector = csv.reader(archive)
    next(lector)

    for fila in lector:
        origen = int(fila[0])
        destino = int(fila[1])
        conexion = [origen, destino]
        conexiones.append(conexion)


with open(nodo_archive, "r") as archive:
    lector = csv.reader(archive)
    next(lector)

    for fila in lector:
        id = int(fila[0])
        latitud = float(fila[1])
        longitud = float(fila[2])
        altitud = float(fila[3])

        nodo = [id, latitud, longitud, altitud]
        nodos.append(nodo)


with open(direccion_archive, "r") as archive:
    lector = csv.reader(archive)
    next(lector)

    for fila in lector:
        nodo_inicial = int(fila[0])
        nodo_final = float(fila[1])


def calcularCoord(n):
    R = 6371000

    _, latitud, longitud, altitud = n

    latitud = radians(latitud)
    longitud = radians(longitud)

    x = (R + altitud) * cos(latitud) * cos(longitud)
    y = (R + altitud) * cos(latitud) * sin(longitud)
    z = (R + altitud) * sin(latitud)

    coordenadas = [x, y, z]

    return coordenadas


def calculardist(nodoi, nodof):
    x1, y1, z1 = coords[nodoi]
    x2, y2, z2 = coords[nodof]

    return sqrt(
        (x2 - x1) ** 2 +
        (y2 - y1) ** 2 +
        (z2 - z1) ** 2
    )


def convertRoute(route, nodos):
    coordenadas_ruta = []

    for id_nodo in route:
        for nodo in nodos:
            if nodo[0] == id_nodo:
                coordenadas_ruta.append(
                    [nodo[1], nodo[2]]
                )
                break

    return coordenadas_ruta


def obtenerNodosRuta(ruta, nodos):
    nodos_ruta = []

    for id_nodo in ruta:
        for nodo in nodos:
            if nodo[0] == id_nodo:
                nodos_ruta.append(nodo)

    return nodos_ruta


for nodo in nodos:
    id_nodo = nodo[0]
    coord = calcularCoord(nodo)

    coords[id_nodo] = coord


for i in range(len(conexiones)):
    nodoi, nodof = conexiones[i]

    distancia = calculardist(nodoi, nodof)

    distancias.append(distancia)


conexiones = [
    conexion + [distancia]
    for conexion, distancia in zip(conexiones, distancias)
]


argumentos = []

for conexion in conexiones:
    argumentos.append(
        ",".join(map(str, conexion))
    )


resultado = subprocess.run(
    ["./programa", str(nodo_inicial), str(nodo_final)]
    + argumentos,
    capture_output=True,
    text=True
)


ruta = []


with open(Evento_archive, "r") as archive:
    reader = csv.reader(archive)
    next(reader)

    for read in reader:
        evento = read[0]
        nodos_ruta = read[2]

        if evento == "PACKAGESEND":
            origen, destino = nodos_ruta.split("-")

            if not ruta:
                ruta.append(int(origen))

            ruta.append(int(destino))


print("RUTA:", ruta)
print("CANTIDAD DE NODOS:", len(nodos))


coords_ruta = convertRoute(ruta, nodos)


nodos_ruta = obtenerNodosRuta(ruta, nodos)


cantidad = len(nodos_ruta)

indices = [
    int(i * (cantidad - 1) / 10)
    for i in range(11)
]


nodos_mostrar = [
    nodos_ruta[i]
    for i in indices
]


mapa = folium.Map(
    location=coords_ruta[0],
    zoom_start=15
)


for nodo in nodos_mostrar:
    id_nodo = nodo[0]
    latitud = nodo[1]
    longitud = nodo[2]
    elevacion = nodo[3]

    if id_nodo == ruta[0]:
        tipo = "origen"
        color = "red"

    elif id_nodo == ruta[-1]:
        tipo = "destino"
        color = "green"

    else:
        tipo = "camino"
        color = "blue"

    informacion = f"""
    <b>Nodo {id_nodo}</b><br>
    Tipo: {tipo}<br>
    Latitud: {latitud}<br>
    Longitud: {longitud}<br>
    Elevación: {elevacion} m
    """

    folium.Marker(
        [latitud, longitud],
        popup=informacion,
        icon=folium.Icon(color=color)
    ).add_to(mapa)


linea = folium.PolyLine(coords_ruta)

linea.add_to(mapa)


plugins.PolyLineTextPath(
    linea,
    "➜",
    repeat=True,
    offset=7,
    attributes={
        "fill": "black",
        "font-weight": "bold",
        "font-size": "16"
    }
).add_to(mapa)


mapa.save("mapa.html")