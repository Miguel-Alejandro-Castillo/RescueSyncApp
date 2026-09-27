# Cómo están organizados los estilos

- **reset.css**: ajustes básicos del navegador (márgenes, padding y tamaño de las cajas).
- **variables.css**: paleta y valores compartidos. Por ejemplo, --primary es el color principal y --primary-hover es el color al interactuar con un botón.
- **globals.css**: tipografía, estructura de página, campos, botones, mensajes y accesibilidad. Las reglas están agrupadas por esos usos.
- **Archivos .module.css**: distribución y detalles exclusivos de cada página o componente, junto a su archivo JSX.

## Dónde hacer un cambio

Para cambiar un color compartido, buscá su variable. Para cambiar todos los campos o botones, usá globals.css. Para ajustar solo el login o el cuadro de una emergencia seleccionada, usá el módulo CSS de esa página.

## Por qué aparecen variables --bs-*

Son opciones de Bootstrap, que ya utiliza el proyecto. Permiten personalizar colores de botones y sus estados (normal, hover, activo y deshabilitado) sin reescribir el componente. En variables.css se conecta la paleta general; en globals.css se ajusta cada tipo de botón.

El orden de carga está en main.jsx: Bootstrap, reset, variables y estilos globales. Mantener ese orden evita que Bootstrap reemplace las personalizaciones.
