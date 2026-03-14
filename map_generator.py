import folium
from folium.plugins import MarkerCluster
import base64
import os
from io import BytesIO
from PIL import Image
from aiogram import Bot
from database import get_all_graffiti


def compress_photo(photo_path, max_width=300, quality=40):
    img = Image.open(photo_path)
    ratio = max_width / img.width
    new_height = int(img.height * ratio)
    img = img.resize((max_width, new_height), Image.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode()


def make_popup_html(img_base64, author, date, description):
    img_section = ""
    if img_base64:
        img_section = f'''
            <div style="width:100%; border-radius:10px; overflow:hidden; margin-bottom:10px;">
                <img src="data:image/jpeg;base64,{img_base64}" 
                     style="width:100%; display:block;">
            </div>
        '''

    return f'''
    <div style="
        width:240px; 
        font-family:'Segoe UI', Arial, sans-serif; 
        padding:0; 
        margin:0;
        line-height:1.4;
    ">
        {img_section}
        <div style="padding:2px 4px;">
            <div style="
                font-size:14px; 
                font-weight:bold; 
                color:#6C3483; 
                margin-bottom:6px;
            ">🎨 {author}</div>
            <div style="
                font-size:12px; 
                color:#666; 
                margin-bottom:4px;
            ">📅 {date}</div>
            <div style="
                font-size:12px; 
                color:#333;
                border-top:1px solid #eee;
                padding-top:6px;
                margin-top:4px;
            ">{description or '<i style="color:#999;">Нет описания</i>'}</div>
        </div>
    </div>
    '''


def make_custom_icon():
    return folium.DivIcon(
        html='''
        <div style="
            background: linear-gradient(135deg, #9B59B6, #6C3483);
            width: 28px; 
            height: 28px; 
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            border: 2px solid white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            <span style="
                transform: rotate(45deg);
                font-size: 13px;
            ">🎨</span>
        </div>
        ''',
        icon_size=(28, 28),
        icon_anchor=(14, 28),
        popup_anchor=(0, -28)
    )


async def generate_map(bot: Bot):
    tbilisi_map = folium.Map(
        location=[41.7151, 44.8271],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    marker_cluster = MarkerCluster(
        name="Граффити",
        options={
            "maxClusterRadius": 30,
            "disableClusteringAtZoom": 14
        }
    ).add_to(tbilisi_map)

    graffiti_list = get_all_graffiti()
    os.makedirs("photos", exist_ok=True)

    for item in graffiti_list:
        g_id, lat, lon, photo_id, author, date, description, added_by, created_at, status = item

        img_base64 = ""
        if photo_id:
            photo_path = f"photos/{g_id}.jpg"
            file = await bot.get_file(photo_id)
            await bot.download_file(file.file_path, photo_path)
            img_base64 = compress_photo(photo_path)

        popup_html = make_popup_html(img_base64, author, date, description)

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=260),
            icon=make_custom_icon()
        ).add_to(marker_cluster)

    tbilisi_map.save("map.html")