# Web Frontend - TanStack React Application

Modern React frontend for the Play Later application built with TanStack Router, TypeScript, and Tailwind CSS.

## 🏗️ Architecture

- **Framework**: TanStack React with file-based routing
- **Build Tool**: Vite with TypeScript
- **Styling**: Tailwind CSS v4 with Shadcn UI components
- **Testing**: Vitest with React Testing Library
- **API Client**: Generated from OpenAPI using @hey-api/openapi-ts
- **State Management**: TanStack Store and React Query

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and pnpm
- Backend API running on http://localhost:8000

### Development Setup

```bash
# From root directory or cd web/
pnpm install
pnpm --filter web dev     # Start dev server on http://localhost:3000
```

### Available Scripts

```bash
pnpm --filter web dev      # Start development server
pnpm --filter web start    # Alias for dev
pnpm --filter web build    # Production build with TypeScript check
pnpm --filter web test     # Run Vitest tests
pnpm --filter web lint     # ESLint check
pnpm --filter web gen:api  # Generate API client from OpenAPI schema
```

## 🧪 Testing

This project follows Test-Driven Development (TDD) practices using [Vitest](https://vitest.dev/) and React Testing Library:

```bash
pnpm --filter web test          # Run all tests
pnpm --filter web test --watch  # Run tests in watch mode
```

### Testing Guidelines

- Write tests first before implementing functionality
- Test components in isolation
- Mock API calls using MSW or similar
- Focus on user behavior over implementation details
- Avoid testing implementation details

## 🎨 Styling

This project uses [Tailwind CSS](https://tailwindcss.com/) v4 for styling with [Shadcn UI](https://ui.shadcn.com/) components.

### Adding Shadcn Components

```bash
pnpx shadcn@latest add [component-name]

# Examples:
pnpx shadcn@latest add button
pnpx shadcn@latest add dialog
pnpx shadcn@latest add form
```



## 🧭 Routing

This project uses [TanStack Router](https://tanstack.com/router) with file-based routing. Routes are managed as files in `src/routes/`.

### File-Based Routing

- Routes are automatically generated from files in `src/routes/`
- Layout is defined in `src/routes/__root.tsx`
- Each route file exports a `Route` object using `createRoute` or `createFileRoute`

### Adding Routes

```bash
# Create a new route file
touch src/routes/about.tsx
```

### Navigation

```tsx
import { Link } from "@tanstack/react-router";

// Simple navigation
<Link to="/about">About</Link>

// With parameters
<Link to="/user/$id" params={{ id: "123" }}>User Profile</Link>
```

### Route Layouts

Global layout is defined in `src/routes/__root.tsx`:

```tsx
import { Outlet, createRootRoute } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'

export const Route = createRootRoute({
  component: () => (
    <>
      <nav>{/* Navigation */}</nav>
      <main>
        <Outlet /> {/* Route content renders here */}
      </main>
      <TanStackRouterDevtools />
    </>
  ),
})
```


## 🔄 Data Fetching

### API Client Generation

The frontend uses a generated TypeScript API client based on the OpenAPI schema:

```bash
pnpm --filter web gen:api
```

This reads from `contract/openapi.json` and outputs to `web/src/shared/api/generated/`.

### TanStack Router Loaders

Load data before route rendering using loaders:

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { apiClient } from '@/shared/api'

export const Route = createFileRoute('/items')({
  loader: async () => {
    const items = await apiClient.getItems()
    return { items }
  },
  component: ItemsPage,
})

function ItemsPage() {
  const { items } = Route.useLoaderData()
  return <div>{/* Render items */}</div>
}
```

### TanStack Query (React Query)

For complex data fetching, caching, and synchronization:

```tsx
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api'

function ItemsComponent() {
  const { data: items, isLoading, error } = useQuery({
    queryKey: ['items'],
    queryFn: () => apiClient.getItems(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>
  
  return <div>{/* Render items */}</div>
}
```

### Data Fetching Best Practices

- Use route loaders for critical data needed for page rendering
- Use TanStack Query for data that can be loaded after initial render
- Implement proper loading and error states
- Cache API responses appropriately
- Handle optimistic updates for better UX

## 🏪 State Management

### TanStack Store

For local component and global state management:

```bash
pnpm add @tanstack/store
```

#### Basic Store Usage

```tsx
import { useStore } from "@tanstack/react-store"
import { Store } from "@tanstack/store"

// Create a store
const userStore = new Store({
  name: '',
  email: '',
  isAuthenticated: false
})

function UserProfile() {
  const user = useStore(userStore)
  
  const updateName = (name: string) => {
    userStore.setState(prev => ({ ...prev, name }))
  }

  return <div>{/* Component JSX */}</div>
}
```

#### Derived State

```tsx
import { Store, Derived } from "@tanstack/store"

const itemsStore = new Store([])
const filteredItemsStore = new Derived({
  fn: () => itemsStore.state.filter(item => item.active),
  deps: [itemsStore],
})
filteredItemsStore.mount()
```

### TanStack Query State

For server state management, TanStack Query handles caching, synchronization, and optimistic updates automatically.

## 📁 Project Structure

```
web/
├── src/
│   ├── routes/              # File-based routing
│   │   ├── __root.tsx      # Root layout
│   │   ├── index.tsx       # Home page
│   │   └── about.tsx       # About page
│   ├── components/         # Reusable components
│   │   ├── ui/            # Shadcn UI components
│   │   └── common/        # Common components
│   ├── shared/            # Shared utilities
│   │   ├── api/          # Generated API client
│   │   ├── lib/          # Utility functions
│   │   └── types/        # TypeScript types
│   ├── hooks/            # Custom React hooks
│   ├── stores/           # TanStack stores
│   └── styles/           # CSS files
├── public/               # Static assets
├── components.json       # Shadcn UI configuration
├── tsconfig.json        # TypeScript configuration
├── vite.config.ts       # Vite configuration
└── package.json         # Dependencies and scripts
```

## 🔧 Code Style Guidelines

- Use functional components with hooks
- Implement proper TypeScript typing (avoid `any`)
- Follow TanStack Router file-based routing conventions
- Use Shadcn UI components when available
- Prefer composition over inheritance
- Use meaningful variable and function names
- Use kebab-case for file names
- Use named exports instead of default exports

## 🚀 Deployment

Build for production:

```bash
pnpm --filter web build
```

The build output will be in the `dist/` directory, ready for deployment to any static hosting service.

## 🐛 Troubleshooting

- **Build failures**: Check TypeScript errors first
- **API client errors**: Ensure the OpenAPI schema is valid and regenerate client
- **Route errors**: Verify file-based routing structure in `src/routes/`
- **Component errors**: Check Shadcn UI component installation and imports
