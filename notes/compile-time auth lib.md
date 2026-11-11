Note: Google's AI suggested the following. Treat it with suspicion.

You have two clean ways to wire this up depending on your project setup:
========================================================================

Option A: Environment Variable / Runtime Factory (Recommended for Bundlers like Vite, Webpack, or Node)
-------------------------------------------------------------------------------------------------------

Export a singleton instance of the auth service based on an environment flag.
```typescript
// auth.factory.ts
import { IAuthService } from './auth.interface';
import { AmplifyAuthService } from './amplify-auth.service';
import { DummyAuthService } from './dummy-auth.service';

const useDummyAuth = process.env.VITE_USE_DUMMY_AUTH === 'true'; // or process.env.REACT_APP_..., or Node process.env

export const authService: IAuthService = useDummyAuth
? new DummyAuthService()
: new AmplifyAuthService();
```

In your .env.development (or .env.local), you set:
```env
VITE_USE_DUMMY_AUTH=true
```

And in production:
```env
VITE_USE_DUMMY_AUTH=false
```

Option B: TypeScript Path Aliasing (Build-time replacement)
-----------------------------------------------------------

If you don't even want the Amplify auth code bundled into your local development chunks, you can use Webpack/Vite alias 
or TypeScript paths to swap out the module file itself.

1. Create an entry file auth.service.ts in your core code that exports authService.
2. Create auth.service.dev.ts (using DummyAuthService) and auth.service.prod.ts (using AmplifyAuthService).
3. Configure your bundler (Vite or Webpack) to alias path/to/auth.service to path/to/auth.service.dev.ts when running 
   locally, or auth.service.prod.ts for production.

Why this approach works well:

* Type Safety: TypeScript enforces that both the real Amplify wrapper and your dummy module implement the exact same 
  contract (IAuthService).
* Zero Pollution: Your business logic, UI components, and state management only import authService from your 
  factory/provider, remaining completely agnostic of AWS.
* Testability: You can easily reuse DummyAuthService (or write a mock/spy version of IAuthService) inside your unit and 
  integration tests.

If you share your framework or bundler (e.g., Next.js, Vite, React, Node/Express), I can tailor the exact configuration 
code for your environment variables or path aliases.
