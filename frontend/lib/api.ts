// API client for communicating with FastAPI backend
import type {
  User,
  UserProfile,
  Token,
  Video,
  VideoStreamResponse,
  FollowResponse,
  UnfollowResponse,
  RegisterData,
  LoginData,
  UploadVideoData,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Token management
export const getToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
};

export const setToken = (token: string): void => {
  if (typeof window === "undefined") return;
  localStorage.setItem("access_token", token);
};

export const removeToken = (): void => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("access_token");
};

export const getUser = (): User | null => {
  if (typeof window === "undefined") return null;
  const userStr = localStorage.getItem("user");
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
};

export const setUser = (user: User): void => {
  if (typeof window === "undefined") return;
  localStorage.setItem("user", JSON.stringify(user));
};

export const removeUser = (): void => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("user");
};

// Helper function for API requests
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

// Authentication endpoints
export async function register(data: RegisterData): Promise<{ message: string }> {
  const formData = new URLSearchParams();
  formData.append("username", data.username);
  formData.append("email", data.email);
  formData.append("password", data.password);

  return apiRequest<{ message: string }>("/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });
}

export async function login(data: LoginData): Promise<Token> {
  const formData = new URLSearchParams();
  formData.append("username", data.username);
  formData.append("password", data.password);
  formData.append("grant_type", "password");

  const token = await apiRequest<Token>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  // Store token and user
  setToken(token.access_token);
  setUser(token.user);

  return token;
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

// Video endpoints
export async function listVideos(): Promise<Video[]> {
  return apiRequest<Video[]>("/videos");
}

export async function getVideo(videoId: string): Promise<Video> {
  return apiRequest<Video>(`/videos/${videoId}`);
}

export async function getVideoStream(videoId: string): Promise<VideoStreamResponse> {
  return apiRequest<VideoStreamResponse>(`/videos/${videoId}/stream`);
}

export async function uploadVideo(data: UploadVideoData): Promise<Video> {
  const formData = new FormData();
  formData.append("title", data.title);
  formData.append("file", data.file);
  if (data.recipe) {
    formData.append("recipe", data.recipe);
  }
  formData.append("visibility", data.visibility || "public");

  return apiRequest<Video>("/videos", {
    method: "POST",
    body: formData,
  });
}

// User endpoints
export async function getUserProfile(userId: string): Promise<UserProfile> {
  return apiRequest<UserProfile>(`/users/${userId}`);
}

export async function getUserVideos(userId: string): Promise<Video[]> {
  return apiRequest<Video[]>(`/users/${userId}/videos`);
}

export async function followUser(userId: string): Promise<FollowResponse> {
  return apiRequest<FollowResponse>(`/users/${userId}/follow`, {
    method: "POST",
  });
}

export async function unfollowUser(userId: string): Promise<UnfollowResponse> {
  return apiRequest<UnfollowResponse>(`/users/${userId}/follow`, {
    method: "DELETE",
  });
}

export async function getFollowers(userId: string): Promise<User[]> {
  return apiRequest<User[]>(`/users/${userId}/followers`);
}

export async function getFollowing(userId: string): Promise<User[]> {
  return apiRequest<User[]>(`/users/${userId}/following`);
}

// Feed endpoint
export async function getFeed(): Promise<Video[]> {
  return apiRequest<Video[]>("/feed");
}
