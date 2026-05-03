import express from 'express';
import session from 'express-session';
import { createKindeServerClient, GrantType, SessionManager } from '@kinde-oss/kinde-typescript-sdk';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
import { neon } from '@neondatabase/serverless';

dotenv.config();
const sql = neon(process.env.DATABASE_URL!);

const app = express();
const PORT = 3000;

declare module 'express-session' {
    interface SessionData {
        accessToken?: string;
        idToken?: string;
        userInfo?: any;
        userName?: string;
        userEmail?: string;
    }
}

app.use(session({
    secret: process.env.JWT_SECRET || 'your_secret_key',
    resave: true,
    saveUninitialized: true,
    cookie: {
        secure: false,
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
        httpOnly: true,
        sameSite: 'lax',
    }
}));


const createSessionManager = (req: any): SessionManager => ({
    getSessionItem: async (key: string) => req.session?.[key],
    setSessionItem: async (key: string, value: any) => {
        if(!req.session) req.session = {};
        req.session[key] = value;
    } ,

    removeSessionItem: async (key: string) => {
        if(req.session) delete req.session[key];
    },
    destroySession: async () => {
        req.session = {};
    }
});

const kindeClient = createKindeServerClient(GrantType.AUTHORIZATION_CODE,{
    authDomain: process.env.KINDE_ISSUER_URL!,
    clientId: process.env.KINDE_CLIENT_ID!,
    clientSecret: process.env.KINDE_CLIENT_SECRET!,
    redirectURL: '<http://localhost:3000/callback>',
    logoutRedirectURL: '<http://localhost:3000>',
});

app.get('/', (req: any, res: any) => {
    const token = req.session?.accessToken;
    const userInfo = req.session?.userInfo;

    if(token) {

    } else {

    }
});

app.get('/login', async (req: any, res: any) => {
    try {
        const sessionManager = createSessionManager(req);
        const loginUrl = await kindeClient.login(sessionManager);
        res.redirect(loginUrl.toString());
    } catch(error) {
        console.error("Error during login:", error);
        res.status(500).send("Login failed");
    }
});

// Callback route
app.get('/callback', async (req, res) => {
  try {
    const sessionManager = createSessionManager(req);
    const fullUrl = `http://${req.headers.host}${req.url}`;
    console.log('Callback URL:', fullUrl);
    
    // Extract the authorization code from the URL
    const url = new URL(fullUrl);
    const code = url.searchParams.get('code');
    
    if (!code) {
      return res.status(400).send('No authorization code received');
    }
    
    // Manually exchange the code for tokens
    const tokenResponse = await fetch(`${process.env.KINDE_ISSUER_URL}/oauth2/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: process.env.KINDE_CLIENT_ID!,
        client_secret: process.env.KINDE_CLIENT_SECRET!,
        code: code,
        redirect_uri: 'http://localhost:3000/callback',
      }),
    });
    
    const tokenData = await tokenResponse.json();
    console.log('Token response:', tokenData);
    
    if (tokenData.access_token) {
      // Store tokens in session for persistence
      req.session.accessToken = tokenData.access_token;
      req.session.idToken = tokenData.id_token;
      req.session.userInfo = tokenData;
      
      // Decode the ID token to get user info
      const idToken = tokenData.id_token;
      const user = JSON.parse(Buffer.from(idToken.split('.')[1], 'base64').toString());
      console.log('👤 User info from ID token:', user);
      
      // Store user info in session for easy access
      req.session.userName = user.given_name || user.name || 'User';
      req.session.userEmail = user.email || 'user@example.com';
      
      // Automatically create user in database
      try {
        const userId = user.sub;
        const userName = user.given_name || user.name || 'User';
        const userEmail = user.email || 'user@example.com';
        
        // Check if user already exists
        const existingUser = await sql`
          SELECT * FROM users WHERE user_id = ${userId}
        `;
        
        if (existingUser.length === 0) {
          // Create new user
          await sql`
            INSERT INTO users (user_id, name, email, subscription_status, plan, free_todos_used)
            VALUES (${userId}, ${userName}, ${userEmail}, 'free', 'free', 0)
          `;
          console.log('✅ User automatically created in database:', userName, userEmail);
        } else {
          // Update existing user info
          await sql`
            UPDATE users 
            SET name = ${userName}, email = ${userEmail}
            WHERE user_id = ${userId}
          `;
          console.log('✅ User info updated in database:', userName, userEmail);
        }
      } catch (error) {
        console.log('⚠️ Could not auto-create user in database:', error);
      }
      
      // Redirect to home page after successful authentication
      res.redirect('/');
    } else {
      console.log('No access token received');
      res.status(400).send('Authentication failed - no access token received');
    }
  } catch (error) {
    console.error('Callback error:', error);
    res.status(500).send(`Authentication failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
});

app.get('/logout', async (req: any, res: any) => {
    try {
       req.session.destroy((err: any) => {
        if(err) console.log('Session destroy error:',err);
        res.redirect('/');
       })
    } catch(error) {
        console.error("Error during logout:", error);
        res.status(500).send("Logout failed");
    }
});


app.listen(PORT, () => {
  console.log(`🚀 Kinde Auth Server running at http://localhost:${PORT}`);
  console.log('📋 Open your browser and go to http://localhost:3000');
  console.log('🔐 Login with your Kinde account to get a real JWT token');
});