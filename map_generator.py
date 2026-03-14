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
            width: 32px; 
            height: 32px; 
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
        ">
            <svg width="28" height="28" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <!-- Колпачок -->
                <rect x="35" y="5" width="20" height="12" rx="3" fill="#E74C3C"/>
                <!-- Распылитель -->
                <rect x="42" y="0" width="6" height="8" rx="2" fill="#C0392B"/>
                <!-- Тело баллона -->
                <rect x="28" y="17" width="34" height="55" rx="6" fill="url(#grad)"/>
                <!-- Полоса на баллоне -->
                <rect x="28" y="40" width="34" height="14" fill="#6C3483" opacity="0.9"/>
                <!-- Дно -->
                <rect x="30" y="72" width="30" height="8" rx="3" fill="#7D3C98"/>
                <!-- Брызги -->
                <circle cx="75" cy="15" r="3" fill="#9B59B6" opacity="0.7"/>
                <circle cx="82" cy="22" r="2" fill="#AF7AC5" opacity="0.5"/>
                <circle cx="78" cy="28" r="2.5" fill="#D2B4DE" opacity="0.6"/>
                <!-- Градиент -->
                <defs>
                    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#9B59B6"/>
                        <stop offset="100%" style="stop-color:#6C3483"/>
                    </linearGradient>
                </defs>
            </svg>
        </div>
        ''',
        icon_size=(32, 32),
        icon_anchor=(16, 32),
        popup_anchor=(0, -32)
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