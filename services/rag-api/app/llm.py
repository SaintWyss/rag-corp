import os
import google.generativeai as genai

# Usamos la misma clave que ya configuramos
API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

def generate_rag_answer(query: str, context_chunks: list[str]) -> str:
    if not API_KEY:
        return "Error: API Key no configurada."

    # Unimos los fragmentos encontrados en un solo texto
    context_text = "\n\n".join(context_chunks)
    
    # El Prompt: La instrucción maestra para la IA
    prompt = f"""
    Actúa como un asistente experto de la empresa RAG Corp.
    Tu misión es responder la pregunta del usuario basándote EXCLUSIVAMENTE en el contexto proporcionado abajo.
    
    Reglas:
    1. Si la respuesta no está en el contexto, decí "No tengo información suficiente en mis documentos".
    2. Sé conciso y profesional.
    3. Respondé siempre en español.

    --- CONTEXTO ---
    {context_text}
    ----------------
    
    Pregunta: {query}
    Respuesta:
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generando respuesta: {str(e)}"
