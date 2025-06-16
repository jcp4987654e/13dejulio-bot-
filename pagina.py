import streamlit as st
import groq
import json # Importamos la librería para manejar archivos JSON

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Chatbot del Instituto 13 de Julio",
    page_icon="🎓",
    layout="centered"
)

# --- CONSTANTES Y CONFIGURACIÓN INICIAL ---

MODELOS = ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"]

# 1. COMPORTAMIENTO (SYSTEM PROMPT)
# Esta es la personalidad y las reglas que el bot seguirá siempre.
SYSTEM_PROMPT = """
Eres un asistente virtual experto del "Instituto 13 de Julio".
Tu nombre es "TecnoBot". Eres amable, servicial y extremadamente eficiente.
Tu única función es responder preguntas relacionadas con el instituto.
Basa tus respuestas estrictamente en el CONTEXTO RELEVANTE que se te proporciona.
Si la pregunta del usuario no tiene que ver con el instituto o el contexto provisto,
responde amablemente que no puedes ayudar con ese tema, ya que tu especialidad es el instituto.
No inventes información. Si no sabes la respuesta, di que no tienes esa información y que
sugieres contactar a la secretaría.
Siempre preséntate como "TecnoBot" en tu primer saludo.
"""

# --- FUNCIONES PRINCIPALES ---

def cargar_base_de_conocimiento(ruta_archivo='conocimiento.json'):
    """
    Carga la base de conocimientos desde el archivo JSON externo.
    """
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Error Crítico: No se encontró el archivo '{ruta_archivo}'. Asegúrate de que exista en la misma carpeta que este script.")
        return None
    except json.JSONDecodeError:
        st.error(f"Error Crítico: El archivo '{ruta_archivo}' no tiene un formato JSON válido.")
        return None

def buscar_contexto_relevante(query, base_de_conocimiento):
    """
    Busca palabras clave del query en la base de conocimientos para encontrar información relevante.
    """
    if base_de_conocimiento is None:
        return "Error: la base de conocimientos no está disponible."
        
    query_lower = query.lower()
    contexto_encontrado = ""
    for keyword, content in base_de_conocimiento.items():
        if keyword in query_lower:
            contexto_encontrado += f"- {content}\n"
    
    if not contexto_encontrado:
        # Si no encuentra una palabra clave, le pasa el dato general del instituto.
        return base_de_conocimiento.get("instituto", "No se encontró contexto específico.")
    return contexto_encontrado

def generar_respuesta_modelo(cliente_groq, modelo_seleccionado, historial_chat):
    """
    Envía la petición a la API de Groq con todo el contexto y el historial.
    """
    try:
        respuesta = cliente_groq.chat.completions.create(
            model=modelo_seleccionado,
            messages=historial_chat,
            temperature=0.7, # Un balance entre creatividad y precisión
            max_tokens=1024,
        )
        return respuesta.choices[0].message.content
    except Exception as e:
        st.error(f"Ocurrió un error al contactar la API de Groq: {e}")
        return None

# --- APLICACIÓN PRINCIPAL DE STREAMLIT ---

def main():
    st.title("🎓 Chatbot del Instituto 13 de Julio")
    st.write("Tu asistente virtual para consultas sobre el instituto.")

    base_de_conocimiento = cargar_base_de_conocimiento()
    if base_de_conocimiento is None:
        st.stop()

    with st.sidebar:
        st.header("Configuración")
        modelo_seleccionado = st.selectbox(
            "Elige tu modelo de IA:",
            MODELOS,
            index=1,
            help="Llama3-70b es más potente, Llama3-8b es más rápido."
        )
        try:
            cliente_groq = groq.Groq(api_key=st.secrets["GROQ_API_KEY"])
        except Exception:
            st.error("API Key de Groq no configurada. Ve a 'Settings > Secrets' y añade tu clave.")
            st.stop()
        st.info("Este chatbot recuerda la conversación actual para dar respuestas más coherentes.")

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = [
            {"role": "assistant", "content": "¡Hola! Soy TecnoBot, el asistente virtual del Instituto 13 de Julio. ¿En qué puedo ayudarte?"}
        ]

    for mensaje in st.session_state.mensajes:
        avatar = "🧑‍💻" if mensaje["role"] == "user" else "🤖"
        with st.chat_message(mensaje["role"], avatar=avatar):
            st.markdown(mensaje["content"])

    if prompt_usuario := st.chat_input("Escribe tu pregunta aquí..."):
        st.session_state.mensajes.append({"role": "user", "content": prompt_usuario})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt_usuario)

        # --- AQUÍ OCURRE LA MAGIA ---
        # 1. Se busca información relevante en el JSON.
        contexto_rag = buscar_contexto_relevante(prompt_usuario, base_de_conocimiento)
        
        # 2. Se construye el prompt de sistema dinámico para la llamada a la API.
        system_prompt_con_contexto = f"{SYSTEM_PROMPT}\n\nUsa el siguiente CONTEXTO RELEVANTE para formular tu respuesta:\n{contexto_rag}"
        
        # 3. Se prepara el historial para simular la CACHE o MEMORIA.
        historial_para_api = [{"role": "system", "content": system_prompt_con_contexto}]
        
        # Agregamos los últimos 10 mensajes (5 idas y vueltas) para mantener el contexto.
        mensajes_relevantes = [msg for msg in st.session_state.mensajes if msg['role'] != 'system']
        historial_para_api.extend(mensajes_relevantes[-10:])
        
        # --- LLAMADA AL MODELO Y RESPUESTA ---
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("TecnoBot está pensando..."):
                respuesta_bot = generar_respuesta_modelo(cliente_groq, modelo_seleccionado, historial_para_api)
                if respuesta_bot:
                    st.markdown(respuesta_bot)
                    st.session_state.mensajes.append({"role": "assistant", "content": respuesta_bot})

if __name__ == "__main__":
    main()
