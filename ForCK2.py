import pyautogui
import tkinter as tk
from PIL import Image, ImageEnhance, ImageOps
import requests
import re
from tkinter import messagebox
from pynput import keyboard

# OCR.Space API Anahtarı
OCR_API_KEY = "K83429945588957"

# MyMemory API Anahtarı
TRANSLATION_API_KEY = "5b9927f9b924d76efdf8"

# Tkinter penceresi için global değişken
root = None
canvas = None

# Seçim alanı için global değişkenler
start_x, start_y, end_x, end_y = None, None, None, None
selecting = False

# Pencere durumu için global değişken
window_visible = False

def capture_screenshot():
    global start_x, start_y, end_x, end_y
    print("📸 Ekran görüntüsü alınıyor...")
    
    left = min(start_x, end_x)
    top = min(start_y, end_y)
    width = abs(end_x - start_x)
    height = abs(end_y - start_y)
    
    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    screenshot_path = "selected_area.png"
    screenshot.save(screenshot_path)
    print(f"Ekran görüntüsü kaydedildi: {screenshot_path}")
    return screenshot

def process_image(img):
    img = img.resize((img.width * 3, img.height * 3))
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(3.0)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(3.0)
    img = img.convert('L')
    img = ImageOps.autocontrast(img)
    threshold = 128
    img = img.point(lambda p: 255 if p > threshold else 0, mode='1')
    return img

def ocr_space(image_path):
    url = "https://api.ocr.space/parse/image"
    try:
        with open(image_path, 'rb') as image_file:
            response = requests.post(
                url,
                files={"file": image_file},
                data={
                    "apikey": OCR_API_KEY,
                    "language": "eng",
                    "isOverlayRequired": True,
                    "scale": True,
                    "OCREngine": 2
                },
                timeout=10
            )
        result = response.json()
        
        if result.get("ParsedResults") is None:
            print("OCR.Space API hatası: Geçersiz yanıt.")
            return None
        
        extracted_text = result["ParsedResults"][0]["ParsedText"]
        return extracted_text.strip()
    except requests.exceptions.RequestException as e:
        print(f"OCR.Space API hatası: {e}")
        return None

def clean_text(text):
    cleaned = re.sub(r'[^\w\s.,:!?]', '', text)
    cleaned = re.sub(r'\btides\b', 'titles', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def translate_text(text):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair=en|tr&key={TRANSLATION_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            translation = result.get("responseData", {}).get("translatedText", "Çeviri başarısız")
            return translation
        else:
            print(f"MyMemory API hatası: {response.status_code}, {response.text}")
            return f"Çeviri hatası: {response.text}"
    except requests.exceptions.RequestException as e:
        print(f"MyMemory API bağlantı hatası: {e}")
        return f"Çeviri hatası: {str(e)}"
    except Exception as e:
        print(f"MyMemory API hatası: {e}")
        return f"Çeviri hatası: {str(e)}"

def capture_and_translate():
    try:
        screenshot = capture_screenshot()
        processed_image = process_image(screenshot)
        processed_image_path = "temp_processed.png"
        processed_image.save(processed_image_path)
        
        extracted_text = ocr_space(processed_image_path)
        
        if not extracted_text:
            print("Hiçbir metin bulunamadı.")
            return
        
        print("📄 Tespit Edilen Metin:")
        print(extracted_text)
        
        cleaned_text = clean_text(extracted_text)
        
        if not cleaned_text:
            print("Hiçbir geçerli metin bulunamadı.")
            return
        
        print("🔍 Seçilen Cümle:")
        print(cleaned_text)
        
        sentences = split_into_sentences(cleaned_text)
        
        translations = []
        for sentence in sentences:
            translation = translate_text(sentence)
            translations.append(f"{sentence} -> {translation}")
        
        messagebox.showinfo("Çeviri Sonucu", "\n".join(translations))
    except Exception as e:
        print(f"Hata: {e}")

def on_mouse_down(event):
    global start_x, start_y, selecting
    start_x, start_y = event.x, event.y
    selecting = True

def on_mouse_move(event):
    global start_x, start_y, end_x, end_y, selecting
    if selecting:
        end_x, end_y = event.x, event.y  # Düzeltme burada yapıldı
        canvas.delete("selection")
        canvas.create_rectangle(start_x, start_y, end_x, end_y, outline="red", width=2, tags="selection")

def on_mouse_up(event):
    global start_x, start_y, end_x, end_y, selecting
    end_x, end_y = event.x, event.y
    selecting = False
    canvas.delete("selection")
    canvas.create_rectangle(start_x, start_y, end_x, end_y, outline="red", width=2, tags="selection")
    capture_and_translate()

def create_gui():
    global root, canvas
    root = tk.Tk()
    root.title("Metin Çevirisi")
    root.attributes("-fullscreen", True)
    root.configure(bg='white')
    
    canvas = tk.Canvas(root, bg='white', highlightthickness=0)
    canvas.pack(expand=True, fill=tk.BOTH)
    canvas.configure(bg='white')
    
    root.attributes("-alpha", 0.1)
    
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    
    root.mainloop()

def toggle_window():
    global window_visible, root
    if window_visible:
        root.withdraw()
        window_visible = False
    else:
        root.deiconify()
        root.attributes("-topmost", True)
        window_visible = True

def on_press(key):
    try:
        if key.char == '+':
            toggle_window()
    except AttributeError:
        pass

keyboard_listener = keyboard.Listener(on_press=on_press)
keyboard_listener.start()

create_gui()
