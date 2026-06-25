# Carpeta `uis`

Esta carpeta contiene **todas las interfaces de usuario** relacionadas con la compañía para el proyecto transversal de AI Engineering (por ejemplo: aplicaciones web, dashboards internos, portales de clientes, apps de Streamlit/Gradio, etc.).

Cada subcarpeta dentro de `uis/` debe corresponder a **una interfaz de usuario concreta** (por ejemplo `website`, `backoffice`) e incluir su propia documentación técnica y funcional.

- **Propósito principal**: centralizar en un único lugar todas las aplicaciones frontend que dan soporte a los casos de uso de la compañía.
- **Recomendación**: documenta en este archivo (o en sub-READMEs) las aplicaciones que vayas añadiendo, su objetivo, tecnología usada y cómo ejecutarlas.


## Progreso

### `talent-pipeline-tracker`

Herramienta interna de **People & Talent** para gestionar el pipeline de candidaturas de HealthCore.

- **Tecnología**: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- **API**: [Talent Tracker API](https://playground.4geeks.com/tracker/api/v1/docs)
- **Ejecución**:

```bash
cd uis/talent-pipeline-tracker
npm install
npm run dev
```

Documentación detallada en [`talent-pipeline-tracker/README.md`](./talent-pipeline-tracker/README.md).
