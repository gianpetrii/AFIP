---
alwaysApply: true
---

# Reglas del Proyecto

## Gestión de Dependencias

**NUNCA instalar paquetes directamente**
- ❌ No ejecutar `npm install`, `npm add`, `yarn add`, `pnpm add`, etc.
- ✅ Proporcionar el comando exacto para que el usuario lo ejecute
- Ejemplo: "Necesitas instalar X. Ejecuta: `npm install nombre-paquete`"

## Control de Versiones

**NUNCA versionar código automáticamente**
- ❌ No ejecutar `git add`, `git commit`, `git push` sin solicitud explícita
- ✅ Solo versionar cuando el usuario lo pida explícitamente
- ⚠️ No asumir que porque se pidió una vez, todo debe versionarse automáticamente
- Esperar instrucción explícita cada vez: "versiona los cambios", "commitea esto", etc.

## Uso de Terminales

**El usuario ejecuta y valida el flujo de desarrollo; el agente investiga y entrega código.**

**Permitido sin pedir:**
- Comandos de lectura y diagnóstico: `git status`, `git diff`, `git log`, inspección de archivos, búsqueda en el código, etc.

**Prohibido sin pedir explícito:**
- ❌ `npm run dev`, `npm run build`, `npm test`, `npm run lint`
- ❌ Instalación de paquetes
- ❌ `git add`, `git commit`, `git push`
- ❌ Servidores o procesos largos en background

## Estimación de Tareas

**Estimar basándose en capacidad del agente, no en desarrolladores humanos**
- ✅ Pensar en cuántas tool calls y pasos requiere la tarea
- ✅ Considerar la complejidad técnica real
- ❌ No usar referencias temporales humanas ("2-3 días", "una semana")
- Enfoque: "Esto requiere modificar X archivos y crear Y componentes"

## Estilo de Comunicación

**Ser breve, directo y propositivo**
- ✅ Ir directo al punto, sin rodeos
- ✅ Explicar solo lo necesario
- ✅ Siempre ofrecer mejoras cuando las identifiques
- ❌ Evitar explicaciones largas innecesarias
- ❌ No repetir información obvia

**Formato para sugerencias:**
```
"Listo. [Breve explicación de lo que se hizo]

Sugerencia: [Mejora identificada] - ¿te gustaría implementarla?"
```

## Prioridad: Experiencia de Usuario

**Priorizar UX cuando la tarea involucre interfaz**
- ✅ Flujos claros e intuitivos
- ✅ Feedback visual inmediato (loaders, toasts, estados de carga)
- ✅ Estados vacíos informativos con CTAs claras
- ✅ Diseño responsive cuando aplique
- ✅ Textos de acciones descriptivos y claros
- ⚠️ Antes de implementar UI, preguntar: "¿Esto mejora la experiencia del usuario?"

## Convenciones de Código

- Respetar convenciones existentes del repositorio (nombres, carpetas, estilo del código actual)
- No introducir dependencias ni patrones nuevos sin acordarlo con el usuario
- Tipado estricto cuando el proyecto use TypeScript
- Cambios acotados al alcance pedido; evitar refactors colaterales
- ❌ No crear archivos de documentación `.md` (README, CHANGELOG, etc.) salvo pedido explícito
