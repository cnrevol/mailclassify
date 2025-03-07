import axios from 'axios';
import { Email, ApiResponse } from './types';

const API_BASE_URL = 'http://localhost:8000/api';

export const fetchEmails = async (email: string, limit?: number, hours?: number) => {
    const params = new URLSearchParams();
    params.append('email', email);
    if (limit) params.append('limit', limit.toString());
    if (hours) params.append('hours', hours.toString());
    
    const response = await axios.get<ApiResponse<Email[]>>(`${API_BASE_URL}/mail/outlook/?${params}`);
    return response.data;
};

export const markEmailAsRead = async (emailId: number) => {
    const response = await axios.post<ApiResponse<Email>>(`${API_BASE_URL}/mail/${emailId}/read/`);
    return response.data;
};