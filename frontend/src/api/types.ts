export interface UserMailInfo {
    id: number;
    email: string;
    client_id: string;
    client_secret: string;
    tenant_id: string;
    access_token?: string;
    refresh_token?: string;
    token_expires?: string;
    last_sync_time?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface Email {
    id: number;
    user_mail: number;
    message_id: string;
    subject: string;
    sender: string;
    received_time: string;
    content: string;
    is_read: boolean;
    categories: string;
    importance: string;
    has_attachments: boolean;
    created_at: string;
    updated_at: string;
}

export interface ApiResponse<T> {
    status: number;
    message: string;
    data: T;
}
