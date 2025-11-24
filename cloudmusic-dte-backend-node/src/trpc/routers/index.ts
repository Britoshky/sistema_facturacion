import { router } from '../init';
import { authRouter } from './auth';
import { usersRouter } from './users';
import { companiesRouter } from './companies';
import { companyUsersRouter } from './companyUsers';
import { clientsRouter } from './clients';
import { productsRouter } from './products';
import { certificatesRouter } from './certificates';
import { foliosRouter } from './folios';
import { documentsRouter } from './documents';
import { reportsRouter } from './reports';
import { aiRouter } from './ai';
import { websocketRouter } from './websocket';
import { debugRouter } from './debug';

export const appRouter = router({
  auth: authRouter,
  users: usersRouter,
  companies: companiesRouter,
  companyUsers: companyUsersRouter,
  clients: clientsRouter,
  products: productsRouter,
  certificates: certificatesRouter,
  folios: foliosRouter,
  documents: documentsRouter,
  reports: reportsRouter,
  ai: aiRouter,
  websocket: websocketRouter,
  debug: debugRouter
});

export type AppRouter = typeof appRouter;