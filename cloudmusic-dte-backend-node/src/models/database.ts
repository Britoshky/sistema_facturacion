// Configuración de conexión a Prisma
import { PrismaClient } from '@prisma/client';

// Crear instancia global de Prisma
const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma = globalForPrisma.prisma ?? new PrismaClient({
  log: process.env.NODE_ENV === 'development' ? ['query', 'info', 'warn', 'error'] : ['error'],
});

// Prevenir instancias múltiples en desarrollo
if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;

// Función para conectar y verificar la base de datos
export async function connectDatabase() {
  try {
    await prisma.$connect();
    console.log('✅ Conexión exitosa a PostgreSQL');
    
    // Verificar algunas tablas clave
    const userCount = await prisma.user.count();
    const companyCount = await prisma.company.count();
    
    console.log(`📊 Datos encontrados: ${userCount} usuarios, ${companyCount} empresas`);
  } catch (error) {
    console.error('❌ Error conectando a la base de datos:', error);
    process.exit(1);
  }
}

// Función para desconectar limpiamente
export async function disconnectDatabase() {
  await prisma.$disconnect();
  console.log('🔌 Desconectado de PostgreSQL');
}