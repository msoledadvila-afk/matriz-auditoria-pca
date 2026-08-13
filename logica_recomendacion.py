"""
Lógica de diagnóstico y recomendación de pack.

Es la traducción directa (misma lógica, mismos umbrales) de la función
getRecommendation() del index.html de la Matriz de Auditoría PCA.
Se mantiene en Python -y no en manos del modelo- porque de acá sale
la recomendación comercial y necesitamos que sea 100% determinística.
"""

MENSAJES_CATEGORIA = {
    "tiempo": "Gestión del tiempo: se detecta pérdida significativa de horas en tareas "
              "operativas y búsqueda de información dispersa. Con IA, estos procesos "
              "pueden reducirse en un 60-70%.",
    "procesos": "Procesos operativos: existen tareas repetitivas sin sistematizar y falta "
                "de documentación que genera retrabajo constante. La automatización "
                "inteligente puede liberar horas de trabajo manual semanal.",
    "comunicacion": "Comunicación: la redacción manual y la falta de plantillas consumen "
                    "tiempo valioso. Con un sistema de prompts validados, la producción de "
                    "comunicados puede reducirse de horas a minutos.",
    "documental": "Gestión documental: la información dispersa y la falta de síntesis "
                  "generan fricción operativa y decisiones demoradas. Un sistema de "
                  "procesamiento de documentos con IA puede cambiar esto radicalmente.",
    "decisiones": "Toma de decisiones: la ausencia de criterios claros de delegación y "
                  "priorización impacta en la eficiencia del liderazgo. Sistematizar estas "
                  "decisiones es el paso que libera mayor capacidad estratégica.",
}

TEXTOS_PACK = {
    "autonomia": "Con el {nombre}, implementaremos un sistema personalizado que ataca "
                 "directamente estos cuellos de botella. A través de prompts validados, "
                 "protocolos de delegación inteligente y sesiones de implementación práctica, "
                 "podés recuperar entre 5 y 10 horas semanales que hoy estás perdiendo en operativa.",
    "equipo": "El {nombre} está diseñado para sistematizar exactamente los flujos donde están "
              "los mayores cuellos de botella detectados. Construiremos protocolos de trabajo "
              "colaborativo con IA, una biblioteca de prompts por área y un sistema de "
              "comunicación y documentación que funcione sin depender de la improvisación.",
    "mentoria": "La {nombre} es el camino para rediseñar la arquitectura de tu liderazgo. En las "
                "sesiones 1:1 trabajaremos el Sistema de Delegación Inteligente PCA™, criterios "
                "claros de toma de decisiones y la integración de IA en los momentos estratégicos "
                "de tu rol, sin perder el control ni la humanidad.",
    "institucional": "La {nombre} es la respuesta adecuada para una transformación de este alcance. "
                      "Trabajaremos por etapas: primero ordenamos la arquitectura de cada área, "
                      "luego sistematizamos procesos por nivel (operativo, táctico, estratégico) "
                      "y garantizamos la sostenibilidad del cambio con métricas y seguimiento "
                      "durante 90 días.",
}


def obtener_recomendacion(catalogo, puntajes_por_categoria, total_pct, preguntas_completadas):
    """
    catalogo: el catálogo cargado (dict con "categorias" y "packs")
    puntajes_por_categoria: dict {"tiempo": 18, "procesos": 12, ...} -> suma de puntajes (max 25 c/u)
    total_pct: porcentaje total del diagnóstico (0 a 1)
    preguntas_completadas: cantidad de preguntas respondidas (int)
    """
    pcts = {cat: puntaje / 25 for cat, puntaje in puntajes_por_categoria.items()}
    criticas = [cat for cat, pct in pcts.items() if pct < 0.4]

    if total_pct < 0.35:
        pack_key = "institucional"
        razon = (f"El diagnóstico revela una situación crítica transversal "
                  f"({len(criticas)} de 5 áreas en estado crítico). Se requiere una "
                  f"intervención sistémica que reordene la arquitectura de trabajo desde "
                  f"sus cimientos, en todos los niveles de la organización.")
    elif "decisiones" in criticas and ("procesos" in criticas or "tiempo" in criticas):
        pack_key = "mentoria"
        razon = ("El perfil muestra dificultades estructurales en toma de decisiones "
                  "combinadas con problemas de procesos o tiempo. Esto indica que el "
                  "problema no es solo de herramientas sino de arquitectura de liderazgo: "
                  "el sistema de delegación y los criterios de priorización necesitan ser "
                  "rediseñados.")
    elif ((pcts.get("comunicacion", 1) < 0.55 or "comunicacion" in criticas)
          and (pcts.get("documental", 1) < 0.55 or "documental" in criticas)):
        pack_key = "equipo"
        razon = ("Los cuellos de botella principales están en comunicación y gestión "
                  "documental — áreas que típicamente impactan a equipos completos más "
                  "que a individuos aislados. La solución requiere sistematizar flujos "
                  "colaborativos y protocolos de trabajo conjunto.")
    else:
        pack_key = "autonomia"
        if preguntas_completadas < 25:
            razon = ("Con las respuestas registradas hasta ahora, el perfil apunta a "
                      "oportunidades claras de optimización individual. Con el sistema y "
                      "los prompts correctos, podés recuperar entre 5 y 10 horas semanales "
                      "de forma inmediata.")
        elif total_pct < 0.7:
            razon = ("El diagnóstico identifica oportunidades claras de optimización "
                      "individual en las áreas con menor puntaje. Con el sistema correcto, "
                      "podés recuperar entre 5 y 10 horas semanales desde la primera semana "
                      "de implementación.")
        else:
            razon = ("Tenés una base sólida. Aún así, existen áreas puntuales que, al "
                      "optimizarse con IA de forma estratégica, pueden multiplicar tu "
                      "capacidad de trabajo estratégico y reducir la fricción operativa "
                      "restante.")

    pack = catalogo["packs"][pack_key]

    # top 3 categorías con menor puntaje = principales cuellos de botella
    ordenadas = sorted(pcts.items(), key=lambda item: item[1])
    categorias_por_id = {c["id"]: c for c in catalogo["categorias"]}
    cuellos_de_botella = []
    for cat_id, pct in ordenadas[:3]:
        cat = categorias_por_id[cat_id]
        cuellos_de_botella.append({
            "categoria": cat["label"],
            "icono": cat["icono"],
            "pct": pct,
            "texto": MENSAJES_CATEGORIA[cat_id],
        })

    if total_pct < 0.4:
        nivel = "crítico que requiere intervención urgente"
    elif total_pct < 0.7:
        nivel = "con potencial de mejora significativo"
    else:
        nivel = "con base sólida y oportunidades de optimización"

    nombres_cuellos = ", ".join(c["categoria"].lower() for c in cuellos_de_botella)
    texto_pack = TEXTOS_PACK[pack_key].format(nombre=pack["nombre"])

    texto_recomendacion = (
        f"El diagnóstico muestra un perfil {nivel}. Las áreas con mayor oportunidad de "
        f"mejora son: {nombres_cuellos}.\n\n{texto_pack}\n\n"
        f"Resultado esperado: {pack['resultado']}."
    )

    return {
        "pack_key": pack_key,
        "pack": pack,
        "razon": razon,
        "cuellos_de_botella": cuellos_de_botella,
        "texto_recomendacion": texto_recomendacion,
    }
