import csv
import json
import folium
from branca.element import Element


grafo_archive = "./csv/grafo.csv"
nodo_archive = "./csv/nodos.csv"

nodos_por_id = {}
ids_grafo = set()




with open(nodo_archive, "r", encoding="utf-8") as archive:
    lector = csv.reader(archive)
    next(lector)

    for fila in lector:
        id_nodo = int(fila[0])
        latitud = float(fila[1])
        longitud = float(fila[2])

        nodos_por_id[id_nodo] = {
            "id": id_nodo,
            "lat": latitud,
            "lon": longitud
        }


with open(grafo_archive, "r", encoding="utf-8") as archive:
    lector = csv.reader(archive)
    next(lector)

    for fila in lector:
        origen = int(fila[0])
        destino = int(fila[1])

        ids_grafo.add(origen)
        ids_grafo.add(destino)


nodos_mapa = [
    nodos_por_id[id_nodo]
    for id_nodo in ids_grafo
    if id_nodo in nodos_por_id
]


if not nodos_mapa:
    raise ValueError("No se encontraron nodos para mostrar en el mapa.")


latitud_centro = sum(
    nodo["lat"] for nodo in nodos_mapa
) / len(nodos_mapa)

longitud_centro = sum(
    nodo["lon"] for nodo in nodos_mapa
) / len(nodos_mapa)


mapa = folium.Map(
    location=[latitud_centro, longitud_centro],
    zoom_start=15,
    control_scale=True
)


nodos_json = json.dumps(nodos_mapa)


script = """
window.addEventListener("load", function() {
    var mapFlowMap = __MAPA__;
    var nodos = __NODOS__;

    var seleccion = [];
    var marcadores = [];

    var nodosPorId = {};

    nodos.forEach(function(nodo) {
        nodosPorId[String(nodo.id)] = nodo;
    });

    var lineaRuta = null;

    var bordeRuta = null;

    var flechasRuta = [];

    var ultimaRuta = null;

    var mediosTransporte = {
        caminar: {
            nombre: "A pie",
            velocidad: 5
        },
        bicicleta: {
            nombre: "Bicicleta",
            velocidad: 15
        },
        automovil: {
            nombre: "Automóvil",
            velocidad: 30
        }
    };

    function distanciaMetros(lat1, lon1, lat2, lon2) {
        var R = 6371000;

        var dLat = (lat2 - lat1) * Math.PI / 180;
        var dLon = (lon2 - lon1) * Math.PI / 180;

        var a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) *
            Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);

        return 2 * R * Math.atan2(
            Math.sqrt(a),
            Math.sqrt(1 - a)
        );
    }

    function buscarNodoCercano(lat, lon) {
        var nodoCercano = null;
        var distanciaMinima = Infinity;

        nodos.forEach(function(nodo) {
            var distancia = distanciaMetros(
                lat,
                lon,
                nodo.lat,
                nodo.lon
            );

            if (distancia < distanciaMinima) {
                distanciaMinima = distancia;
                nodoCercano = nodo;
            }
        });

        return {
            nodo: nodoCercano,
            distancia: distanciaMinima
        };
    }

    var panel = L.control({ position: "topright" });

    panel.onAdd = function() {
        var div = L.DomUtil.create("div", "mapflow-panel");
    div.innerHTML = `
        <div class="mapflow-titulo">MapFlow</div>

        <div id="mapflow-estado">
            Haz clic en el mapa para seleccionar el origen.
        </div>

        <div id="mapflow-origen"></div>
        <div id="mapflow-destino"></div>

        <div id="mapflow-resumen"></div>

        <label for="mapflow-medio">Medio de transporte</label>

        <select id="mapflow-medio">
            <option value="caminar">🚶 A pie</option>
            <option value="bicicleta">🚲 Bicicleta</option>
            <option value="automovil">🚗 Automóvil</option>
        </select>

        <div id="mapflow-tiempo"></div>

        <button id="mapflow-reiniciar" type="button">
            Reiniciar selección
        </button>
    `;

        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);

        return div;
    };

    panel.addTo(mapFlowMap);

    document.getElementById("mapflow-medio")
        .addEventListener("change", actualizarTiempoEstimado);

    var estilos = document.createElement("style");

    estilos.textContent = `
        .mapflow-panel {
            background: white;
            padding: 14px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.20);
            width: 245px;
            font-family: Arial, sans-serif;
            color: #222;
        }

        .mapflow-titulo {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2457C5;
        }

        #mapflow-estado {
            font-size: 13px;
            margin-bottom: 12px;
            line-height: 1.5;
        }

        #mapflow-origen, #mapflow-destino {
            font-size: 12px;
            margin: 8px 0;
            overflow-wrap: anywhere;
        }

        #mapflow-reiniciar {
            margin-top: 12px;
            width: 100%;
            padding: 9px;
            border: none;
            border-radius: 6px;
            background: #2457C5;
            color: white;
            cursor: pointer;
        }

        #mapflow-reiniciar:hover {
            background: #17429B;
        }

        #mapflow-medio {
            width: 100%;
            padding: 9px;
            margin-top: 8px;
            border: 1px solid #d0d7e2;
            border-radius: 6px;
            background: white;
            font-size: 14px;
        }

        #mapflow-resumen {
            margin: 12px 0;
            font-size: 14px;
        }

        #mapflow-tiempo {
            margin-top: 10px;
            padding: 10px;
            background: #edf3ff;
            color: #2457C5;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
        }
    `;

    document.head.appendChild(estilos);

    function actualizarPanel() {
        var origen = document.getElementById("mapflow-origen");
        var destino = document.getElementById("mapflow-destino");
        var estado = document.getElementById("mapflow-estado");

        origen.textContent = "";
        destino.textContent = "";

        if (seleccion.length === 0) {
            estado.textContent =
                "Haz clic en el mapa para seleccionar el origen.";
        } else if (seleccion.length === 1) {
            estado.textContent =
                "Origen seleccionado. Haz clic para elegir el destino.";

            origen.textContent =
                "Origen: nodo " + seleccion[0].nodo.id;
        } else {
            estado.textContent =
                "Origen y destino seleccionados.";

            origen.textContent =
                "Origen: nodo " + seleccion[0].nodo.id;

            destino.textContent =
                "Destino: nodo " + seleccion[1].nodo.id;
        }
    }

    function actualizarTiempoEstimado() {
        var salida = document.getElementById("mapflow-tiempo");

        if (!ultimaRuta) {
            salida.textContent = "";
            return;
        }

        var medioSeleccionado =
            document.getElementById("mapflow-medio").value;

        var medio = mediosTransporte[medioSeleccionado];

        var distanciaKm = Number(ultimaRuta.distancia_km);

        var minutos = (distanciaKm / medio.velocidad) * 60;
        var minutosRedondeados = Math.round(minutos);

        var tiempoTexto;

        if (minutosRedondeados < 1) {
            tiempoTexto = "menos de 1 minuto";
        } else if (minutosRedondeados < 60) {
            tiempoTexto = minutosRedondeados + " min";
        } else {
            var horas = Math.floor(minutosRedondeados / 60);
            var minutosRestantes = minutosRedondeados % 60;

            tiempoTexto = horas + " h";

            if (minutosRestantes > 0) {
                tiempoTexto += " " + minutosRestantes + " min";
            }
        }

        salida.textContent =
            "Tiempo estimado (" + medio.nombre + "): " + tiempoTexto;
    }

    mapFlowMap.on("click", function(e) {
        if (seleccion.length >= 2) {
            return;
        }

        var resultado = buscarNodoCercano(
            e.latlng.lat,
            e.latlng.lng
        );

        var nodo = resultado.nodo;

        if (!nodo) {
            return;
        }

        var esOrigen = seleccion.length === 0;
        var tipo = esOrigen ? "Origen" : "Destino";
        var color = esOrigen ? "#E53935" : "#2E9D50";

        seleccion.push({
            nodo: nodo,
            distanciaClic: resultado.distancia
        });

        var marcador = L.circleMarker(
            [nodo.lat, nodo.lon],
            {
                radius: 8,
                color: color,
                fillColor: color,
                fillOpacity: 0.9
            }
        ).addTo(mapFlowMap);

        marcador.bindPopup(
            "<b>" + tipo + "</b><br>" +
            "Nodo OSM: " + nodo.id + "<br>" +
            "Distancia desde el clic: " +
            Math.round(resultado.distancia) + " m"
        ).openPopup();

        marcadores.push(marcador);

                actualizarPanel();

        if (seleccion.length === 2) {
            fetch("/seleccion", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    origen: seleccion[0].nodo.id,
                    destino: seleccion[1].nodo.id
                })
            })
            .then(async response => {
                var datos = await response.json();

                if (!response.ok) {
                    throw new Error(
                        datos.error || "No se pudo calcular la ruta."
                    );
                }

                return datos;
            })
           .then(datos => {
                console.log("Ruta recibida de C++:", datos.ruta);

                var coordenadasRuta = datos.ruta
                    .map(function(id) {
                        return nodosPorId[String(id)];
                    })
                    .filter(function(nodo) {
                        return nodo !== undefined;
                    })
                    .map(function(nodo) {
                        return [nodo.lat, nodo.lon];
                    });

                if (lineaRuta) {
                    mapFlowMap.removeLayer(lineaRuta);
                }

                if (bordeRuta) {
                    mapFlowMap.removeLayer(bordeRuta);
                }

                bordeRuta = L.polyline(coordenadasRuta, {
                    color: "#FFFFFF",
                    weight: 8,
                    opacity: 0.95,
                    lineCap: "round",
                    lineJoin: "round"
                }).addTo(mapFlowMap);

                lineaRuta = L.polyline(coordenadasRuta, {
                    color: "#2457C5",
                    weight: 4,
                    opacity: 1,
                    lineCap: "round",
                    lineJoin: "round"
                }).addTo(mapFlowMap);

                
                flechasRuta.forEach(function(flecha) {
                    mapFlowMap.removeLayer(flecha);
                });

                flechasRuta = [];

                
                for (var i = 0; i < coordenadasRuta.length - 1; i += 3) {
                    var p1 = coordenadasRuta[i];
                    var p2 = coordenadasRuta[i + 1];

                    var lat1 = p1[0] * Math.PI / 180;
                    var lon1 = p1[1] * Math.PI / 180;
                    var lat2 = p2[0] * Math.PI / 180;
                    var lon2 = p2[1] * Math.PI / 180;

                    var dLon = lon2 - lon1;

                    var y = Math.sin(dLon) * Math.cos(lat2);

                    var x =
                        Math.cos(lat1) * Math.sin(lat2) -
                        Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);

                    var angulo = (
                        Math.atan2(y, x) * 180 / Math.PI + 360
                    ) % 360;

                    var latMedia = (p1[0] + p2[0]) / 2;
                    var lonMedia = (p1[1] + p2[1]) / 2;

                    var iconoFlecha = L.divIcon({
                            className: "mapflow-flecha-icon",
                            html:
                                '<div style="' +
                                'display:flex;' +
                                'align-items:center;' +
                                'justify-content:center;' +
                                'width:32px;' +
                                'height:32px;' +
                                'border-radius:50%;' +
                                'background:white;' +
                                'border:2px solid #2457C5;' +
                                'box-shadow:0 2px 5px rgba(0,0,0,0.35);' +
                                'color:#2457C5;' +
                                'font-size:28px;' +
                                'font-weight:900;' +
                                'line-height:1;' +
                                'transform:rotate(' + angulo + 'deg);' +
                                '">↑</div>',
                            iconSize: [36, 36],
                            iconAnchor: [18, 18]
                        });

                    var flecha = L.marker(
                        [latMedia, lonMedia],
                        {
                            icon: iconoFlecha,
                            interactive: false,
                            keyboard: false
                        }
                    ).addTo(mapFlowMap);

                    flechasRuta.push(flecha);
                }

                mapFlowMap.fitBounds(lineaRuta.getBounds(), {
                    padding: [30, 30]
                });

                ultimaRuta = datos;

                document.getElementById("mapflow-estado").textContent =
                    "Ruta calculada correctamente: " +
                    datos.cantidad_nodos + " nodos.";

                document.getElementById("mapflow-resumen").textContent =
                    "Distancia del recorrido: " +
                    datos.distancia_km + " km";

                actualizarTiempoEstimado();
            })
            .catch(error => {
                console.error("Error:", error);

                document.getElementById("mapflow-estado").textContent =
                    "No se pudo calcular la ruta: " + error.message;
            });
        }
    });

    document.getElementById("mapflow-reiniciar")
        .addEventListener("click", function() {
            marcadores.forEach(function(marcador) {
                mapFlowMap.removeLayer(marcador);
            });

            marcadores = [];
            seleccion = [];

            actualizarPanel();
        });
});
"""

script = script.replace("__MAPA__", mapa.get_name())
script = script.replace("__NODOS__", nodos_json)

mapa.get_root().script.add_child(Element(script))

mapa.save("mapa.html")

print("Nodos disponibles:", len(nodos_mapa))
print("Mapa generado: mapa.html")