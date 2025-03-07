import axios from 'axios';
import { UserMailInfo, ApiResponse } from './types';

const API_BASE_URL = 'http://localhost:8000/api';

export const configureMailAccount = async (mailInfo: Omit<UserMailInfo, 'id' | 'created_at' | 'updated_at'>) => {
    const response = await axios.post<ApiResponse<UserMailInfo>>(`${API_BASE_URL}/mail/configure/`, mailInfo);
    return response.data;
};

export const getMailConfiguration = async (email: string) => {
    const response = await axios.get<ApiResponse<UserMailInfo>>(`${API_BASE_URL}/mail/configure/?email=${email}`);
    return response.data;
};