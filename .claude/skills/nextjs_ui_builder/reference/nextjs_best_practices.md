# NextJS Development Best Practices

## Project Structure

### Recommended Folder Organization
```
project-root/
├── components/           # Reusable React components
│   ├── ui/             # Base UI components (buttons, inputs, etc.)
│   ├── forms/          # Form-specific components
│   ├── layout/         # Layout components (headers, footers, etc.)
│   └── sections/       # Larger UI sections
├── pages/              # Next.js pages and API routes
│   ├── api/            # Server-side API routes
│   ├── _app.js         # Custom App component
│   ├── _document.js    # Custom Document component
│   ├── _error.js       # Custom error page
│   └── index.js        # Homepage
├── public/             # Static assets (images, icons, etc.)
├── styles/             # Global and utility styles
│   ├── globals.css     # Global styles
│   ├── Home.module.css # Page-specific styles
│   └── components/     # Component-specific styles
├── lib/                # Utility functions and API helpers
├── hooks/              # Custom React hooks
├── contexts/           # React Context providers
├── types/              # TypeScript type definitions
├── utils/              # General utility functions
└── config/             # Configuration files
```

## Component Development

### Reusable UI Components
```jsx
// components/ui/Button.jsx
import React from 'react';
import PropTypes from 'prop-types';

const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  className = '',
  ...props
}) => {
  const baseClasses = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';

  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    ghost: 'bg-transparent text-gray-900 hover:bg-gray-100 focus:ring-gray-500',
  };

  const sizes = {
    sm: 'text-xs px-3 py-1.5',
    md: 'text-sm px-4 py-2',
    lg: 'text-base px-6 py-3',
  };

  return (
    <button
      className={`${baseClasses} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
};

Button.propTypes = {
  children: PropTypes.node.isRequired,
  variant: PropTypes.oneOf(['primary', 'secondary', 'danger', 'ghost']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  disabled: PropTypes.bool,
  onClick: PropTypes.func,
  className: PropTypes.string,
};

export default Button;
```

### Container/Presentational Pattern
```jsx
// containers/UserProfileContainer.jsx (Container Component)
import React, { useState, useEffect } from 'react';
import UserProfile from '../components/UserProfile';

const UserProfileContainer = ({ userId }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch(`/api/users/${userId}`);
        if (!response.ok) throw new Error('Failed to fetch user');
        const userData = await response.json();
        setUser(userData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [userId]);

  return (
    <UserProfile
      user={user}
      loading={loading}
      error={error}
      onUpdate={handleUpdate}
    />
  );
};

// components/UserProfile.jsx (Presentational Component)
import React from 'react';
import { Card, Avatar, Button } from './ui';

const UserProfile = ({ user, loading, error, onUpdate }) => {
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!user) return <div>No user found</div>;

  return (
    <Card>
      <div className="flex items-center space-x-4">
        <Avatar src={user.avatar} alt={user.name} />
        <div>
          <h2 className="text-xl font-bold">{user.name}</h2>
          <p className="text-gray-600">{user.email}</p>
          <Button onClick={onUpdate}>Update Profile</Button>
        </div>
      </div>
    </Card>
  );
};
```

## Data Fetching Strategies

### Server-Side Rendering (SSR)
```jsx
// pages/user/[id].js
import { useRouter } from 'next/router';

export async function getServerSideProps({ params }) {
  const res = await fetch(`https://api.example.com/users/${params.id}`);
  const user = await res.json();

  return {
    props: {
      user,
    },
  };
}

export default function UserPage({ user }) {
  return <div>{user.name}</div>;
}
```

### Static Site Generation (SSG)
```jsx
// pages/posts/index.js
export async function getStaticProps() {
  const res = await fetch('https://api.example.com/posts');
  const posts = await res.json();

  return {
    props: {
      posts,
    },
    revalidate: 60, // Rebuild page every 60 seconds
  };
}

export default function PostsPage({ posts }) {
  return (
    <div>
      {posts.map(post => (
        <div key={post.id}>{post.title}</div>
      ))}
    </div>
  );
}
```

### Client-Side Data Fetching
```jsx
// components/DataFetcher.jsx
import { useState, useEffect } from 'react';

const DataFetcher = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/api/data');
        const result = await res.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return <div>{/* Render data */}</div>;
};
```

## State Management

### Using React Context
```jsx
// contexts/AppContext.js
import React, { createContext, useContext, useReducer } from 'react';

const AppContext = createContext();

const initialState = {
  user: null,
  theme: 'light',
  notifications: [],
};

function appReducer(state, action) {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'TOGGLE_THEME':
      return { ...state, theme: state.theme === 'light' ? 'dark' : 'light' };
    case 'ADD_NOTIFICATION':
      return {
        ...state,
        notifications: [...state.notifications, action.payload]
      };
    default:
      return state;
  }
}

export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
```

### Custom Hooks for State Logic
```jsx
// hooks/useLocalStorage.js
import { useState, useEffect } from 'react';

export const useLocalStorage = (key, initialValue) => {
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(error);
      return initialValue;
    }
  });

  const setValue = (value) => {
    try {
      setStoredValue(value);
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(error);
    }
  };

  return [storedValue, setValue];
};

// hooks/useApi.js
import { useState, useEffect } from 'react';

export const useApi = (url, options = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(url, options);
        if (!response.ok) throw new Error(response.statusText);
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    if (url) fetchData();
  }, [url, JSON.stringify(options)]);

  const refetch = () => {
    fetchData();
  };

  return { data, loading, error, refetch };
};
```

## Styling Approaches

### Tailwind CSS Configuration
```js
// tailwind.config.js
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
```

### CSS Modules
```css
/* components/Header.module.css */
.header {
  background-color: var(--color-primary);
  padding: 1rem;
}

.navLink {
  color: white;
  text-decoration: none;
  margin-right: 1rem;
}

.navLink:hover {
  text-decoration: underline;
}

.activeNavLink {
  composes: navLink;
  font-weight: bold;
}
```

```jsx
// components/Header.jsx
import styles from './Header.module.css';

const Header = () => {
  return (
    <header className={styles.header}>
      <nav>
        <a href="/" className={styles.navLink}>Home</a>
        <a href="/about" className={styles.activeNavLink}>About</a>
      </nav>
    </header>
  );
};
```

## Performance Optimization

### Code Splitting
```jsx
// pages/index.js
import dynamic from 'next/dynamic';

// Dynamically import heavy components
const HeavyChart = dynamic(() => import('../components/HeavyChart'), {
  loading: () => <p>Loading chart...</p>,
  ssr: false, // Don't render on server
});

// With named exports
const { ChartComponent } = dynamic(() =>
  import('../components/Charts').then((mod) => ({
    default: mod.ChartComponent,
  }))
);

const HomePage = () => {
  return (
    <div>
      <h1>Lightweight homepage</h1>
      <HeavyChart />
    </div>
  );
};
```

### Image Optimization
```jsx
import Image from 'next/image';

const MyImage = () => {
  return (
    <Image
      src="/path/to/image.jpg"
      alt="Description of image"
      width={500}
      height={300}
      placeholder="blur" // Show low-quality placeholder while loading
      blurDataURL="data:image/jpeg;base64..." // Low-quality image placeholder
      priority // Prioritize loading for above-the-fold images
    />
  );
};
```

### Preloading Pages
```jsx
import { useRouter } from 'next/router';
import Link from 'next/link';

const Navigation = () => {
  const router = useRouter();

  return (
    <nav onMouseEnter={() => router.prefetch('/about')}>
      <Link href="/about">About</Link>
    </nav>
  );
};
```

## Forms and Validation

### Form Handling with React Hook Form
```jsx
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

const schema = yup.object({
  email: yup.string().email('Invalid email').required('Email is required'),
  password: yup
    .string()
    .min(8, 'Password must be at least 8 characters')
    .required('Password is required'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('password'), null], 'Passwords must match')
    .required('Confirm password is required'),
}).required();

const SignupForm = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: yupResolver(schema),
  });

  const onSubmit = (data) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('email')}
        placeholder="Email"
      />
      {errors.email && <span>{errors.email.message}</span>}

      <input
        {...register('password')}
        type="password"
        placeholder="Password"
      />
      {errors.password && <span>{errors.password.message}</span>}

      <input
        {...register('confirmPassword')}
        type="password"
        placeholder="Confirm Password"
      />
      {errors.confirmPassword && <span>{errors.confirmPassword.message}</span>}

      <button type="submit">Sign Up</button>
    </form>
  );
};
```

## Testing

### Jest and React Testing Library
```jsx
// components/Button.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button', () => {
  it('renders correctly with children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies correct classes based on variant', () => {
    render(<Button variant="primary">Primary</Button>);
    const button = screen.getByText('Primary');
    expect(button).toHaveClass('bg-blue-600');
  });
});
```

### Mocking API Calls
```jsx
// __mocks__/axios.js
export default {
  get: jest.fn(() => Promise.resolve({ data: {} })),
  post: jest.fn(() => Promise.resolve({ data: {} })),
};

// components/DataComponent.test.jsx
import { render, waitFor } from '@testing-library/react';
import axios from 'axios';
import DataComponent from './DataComponent';

jest.mock('axios');

describe('DataComponent', () => {
  it('fetches and displays data', async () => {
    axios.get.mockResolvedValueOnce({ data: { id: 1, name: 'Test' } });

    render(<DataComponent />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });
});
```

## Security

### Environment Variables
```js
// next.config.js
module.exports = {
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  async redirects() {
    return [
      {
        source: '/http/:path*',
        destination: 'https/:path*',
        permanent: true,
      },
    ];
  },
};
```

### Headers Configuration
```js
// next.config.js
module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
        ],
      },
    ];
  },
};
```

## Internationalization (i18n)
```js
// next.config.js
module.exports = {
  i18n: {
    locales: ['en-US', 'es-ES', 'fr-FR'],
    defaultLocale: 'en-US',
  },
};
```

```jsx
// pages/_app.js
import { appWithTranslation } from 'next-i18next';

function MyApp({ Component, pageProps }) {
  return <Component {...pageProps} />;
}

export default appWithTranslation(MyApp);
```