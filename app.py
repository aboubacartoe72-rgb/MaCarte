from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/route', methods=['POST'])
def get_route():
    # 1. On récupère les données envoyées par le navigateur
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({'error': 'Aucune donnée reçue.'}), 400

    start_lat = data.get('start_lat')
    start_lon = data.get('start_lon')
    dest_name = data.get('dest_name')

    # 2. On vérifie que toutes les infos sont là (évite l'erreur 400)
    if not start_lat or not start_lon:
        return jsonify({'error': 'Position de départ introuvable. Veuillez autoriser la géolocalisation.'}), 400
    if not dest_name:
        return jsonify({'error': 'Veuillez entrer une destination.'}), 400

    # 3. Recherche des coordonnées de la destination (API Nominatim)
    headers = {'User-Agent': 'MonAppMap/1.0 (mon_email@exemple.com)'}
    geo_url = f"https://nominatim.openstreetmap.org/search?format=json&q={dest_name}"
    
    try:
        geo_res = requests.get(geo_url, headers=headers, timeout=10).json()
    except Exception:
        return jsonify({'error': 'Le service de recherche de ville est injoignable.'}), 500

    if not geo_res:
        return jsonify({'error': f'La ville "{dest_name}" est introuvable. Essayez un autre nom.'}), 404

    dest_lat = float(geo_res[0]['lat'])
    dest_lon = float(geo_res[0]['lon'])
    dest_full_name = geo_res[0]['display_name']

    # 4. Calcul de l'itinéraire (API OSRM)
    # Attention : OSRM demande la LONGITUDE d'abord, puis la LATITUDE
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    
    try:
        route_res = requests.get(osrm_url, timeout=10).json()
        
        # Si OSRM ne trouve pas de route (ex: traverser un océan)
        if route_res.get('code') != 'Ok' or 'routes' not in route_res:
            return jsonify({'error': 'Impossible de trouver un itinéraire routier vers cette destination.'}), 400

        route_geometry = route_res['routes'][0]['geometry']
        distance = route_res['routes'][0]['distance'] / 1000  # Convertir en km
        duration = route_res['routes'][0]['duration'] / 60     # Convertir en minutes

        # 5. On renvoie tout au navigateur
        return jsonify({
            'dest_lat': dest_lat,
            'dest_lon': dest_lon,
            'dest_full_name': dest_full_name,
            'route_geometry': route_geometry,
            'distance': round(distance, 1),
            'duration': round(duration)
        })

    except Exception as e:
        return jsonify({'error': 'Erreur lors du calcul du trajet sur le serveur.'}), 500

if __name__ == '__main__':
    app.run(debug=True)