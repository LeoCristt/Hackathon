-- Kong Plugin для проверки домена и добавления AI модели
local WidgetDomainCheckHandler = {
  VERSION = "1.0.0",
  PRIORITY = 1000,
}

local pgmoon = require("pgmoon")

-- Функция подключения к БД
local function connect_to_db(config)
  local pg = pgmoon.new({
    host = config.db_host,
    port = config.db_port,
    database = config.db_name,
    user = config.db_user,
    password = config.db_password
  })

  local success, err = pg:connect()
  if not success then
    kong.log.err("Failed to connect to database: ", err)
    return nil, err
  end

  return pg
end

-- Извлечение домена из Origin или Referer
local function extract_domain(origin)
  if not origin then
    return nil
  end

  -- Убираем протокол (http:// или https://)
  local domain = origin:gsub("^https?://", "")

  -- Убираем порт и путь
  domain = domain:match("^([^:/]+)")

  return domain
end

-- Основная логика плагина
function WidgetDomainCheckHandler:access(config)
  -- Получаем Origin или Referer из заголовков
  local origin = kong.request.get_header("Origin") or kong.request.get_header("Referer")

  if not origin then
    kong.log.warn("No Origin or Referer header found")
    return kong.response.exit(403, {
      message = "Access denied: Origin required",
      code = "NO_ORIGIN"
    })
  end

  kong.log.info("Request from origin: ", origin)

  -- Извлекаем домен
  local domain = extract_domain(origin)
  if not domain then
    return kong.response.exit(403, {
      message = "Access denied: Invalid origin",
      code = "INVALID_ORIGIN"
    })
  end

  kong.log.info("Extracted domain: ", domain)

  -- Подключаемся к БД
  local pg, err = connect_to_db(config)
  if not pg then
    kong.log.err("Database connection failed: ", err)
    return kong.response.exit(500, {
      message = "Internal server error",
      code = "DB_CONNECTION_ERROR"
    })
  end

  -- Проверяем домен в БД
  local query = string.format([[
    SELECT domain, ai_model, is_active, allowed_origins
    FROM widget_domains
    WHERE domain = '%s' AND is_active = true
    LIMIT 1
  ]], pg:escape_literal(domain))

  local result, query_err = pg:query(query)
  pg:keepalive()

  if not result then
    kong.log.err("Query failed: ", query_err)
    return kong.response.exit(500, {
      message = "Internal server error",
      code = "DB_QUERY_ERROR"
    })
  end

  -- Проверяем результат
  if not result[1] then
    kong.log.warn("Domain not found or inactive: ", domain)
    return kong.response.exit(403, {
      message = "Access denied: Domain not authorized",
      code = "DOMAIN_NOT_AUTHORIZED",
      domain = domain
    })
  end

  local domain_config = result[1]
  kong.log.info("Domain found: ", domain, ", AI model: ", domain_config.ai_model)

  -- Проверяем Origin в allowed_origins (если задано)
  if domain_config.allowed_origins and #domain_config.allowed_origins > 0 then
    local origin_allowed = false
    for _, allowed_origin in ipairs(domain_config.allowed_origins) do
      if origin:find(allowed_origin, 1, true) then
        origin_allowed = true
        break
      end
    end

    if not origin_allowed then
      kong.log.warn("Origin not in whitelist: ", origin)
      return kong.response.exit(403, {
        message = "Access denied: Origin not in whitelist",
        code = "ORIGIN_NOT_ALLOWED",
        origin = origin
      })
    end
  end

  -- Добавляем AI модель в заголовок для upstream сервиса
  kong.service.request.set_header("X-Widget-AI-Model", domain_config.ai_model)
  kong.service.request.set_header("X-Widget-Domain", domain)
  kong.service.request.set_header("X-Widget-Authorized", "true")

  kong.log.info("Request authorized for domain: ", domain, ", AI model: ", domain_config.ai_model)
end

return WidgetDomainCheckHandler
