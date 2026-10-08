export class User {
  id!: number;
  username!: string;
  firstName!: string;
  lastName!: string;
  token!: string;
}

export interface LoginResponse {
  token: string;
  user: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
  };
}
