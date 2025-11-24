# Sistema de Facturación CloudMusic DTE

Este proyecto es un sistema integral de facturación electrónica (DTE) con arquitectura moderna, desarrollado para la gestión de documentos tributarios electrónicos en Chile.

## Características principales
- Gestión de clientes, empresas, productos y documentos DTE
- Soporte para múltiples roles de usuario (Super Admin, Admin, Contador, Usuario, Viewer)
- Validación de RUT chileno y flujos de negocio locales
- Integración con IA local (Ollama Llama 3.2 3B)
- Backend Node.js + PostgreSQL + MongoDB
- Frontend React 18 + Next.js 15
- Exportación e importación masiva de datos
- Seguridad y permisos avanzados

## Estructura del proyecto
- **cloudmusic-dte-frontend/**: Aplicación web (React/Next.js)
- **cloudmusic-dte-backend-node/**: API y lógica de negocio (Node.js, tRPC, Prisma)
- **entrega-bases-datos/**: Scripts y ejemplos de bases de datos
- **documentación/**: Diagramas, informes y documentación técnica

## Instalación rápida
1. Clona el repositorio
2. Instala dependencias en frontend y backend
3. Configura tus variables de entorno (`.env`)
4. Ejecuta migraciones de base de datos
5. Inicia frontend y backend

## Licencia
Proyecto académico IPLACEX 2025. Uso educativo y demostrativo.