import folium
from folium.plugins import MarkerCluster
import base64
import os
from aiogram import Bot
from database import get_all_graffiti


async def generate_map(bot: Bot):
    tbilisi_map = folium.Map(
        location=[41.7151, 44.8271],
        zoom_start=13,
        tiles="CartoDB positron"
    )

    marker_cluster = MarkerCluster(name="Граффити").add_to(tbilisi_map)

    graffiti_list = get_all_graffiti()
    os.makedirs("photos", exist_ok=True)

    for item in graffiti_list:
        g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item

        img_tag = ""
        if photo_id:
            photo_path = f"photos/{g_id}.jpg"
            file = await bot.get_file(photo_id)
            await bot.download_file(file.file_path, photo_path)

            with open(photo_path, "rb") as f:
                img_base64 = base64.b64encode(f.read()).decode()
            img_tag = f'<img src="data:image/jpeg;base64,{img_base64}" width="200" style="border-radius:8px; margin-bottom:8px;"><br>'

        popup_text = f"""
        <div style="width:220px; font-family:Arial,sans-serif;">
            {img_tag}
            <b>🎨 Автор:</b> {author}<br>
            <b>📅 Дата:</b> {date}<br>
            <b>📝 Описание:</b> {description or 'Нет описания'}
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=260),
            icon=folium.Icon(color="purple", icon="paint-brush", prefix="fa")
        ).add_to(marker_cluster)

    tbilisi_map.save("map.html")