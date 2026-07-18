export class HealthService {
  constructor(database = { ping: async () => true }) { this.database = database; }
  async basic() { return { status: (await this.database.ping()) ? "ok" : "degraded" }; }
}
