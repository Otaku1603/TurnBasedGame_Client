using System.Collections;
using System.Collections.Generic;
using TurnBasedGame.Services;
using UnityEngine;
using UnityEngine.Networking;

namespace TurnBasedGame.Core
{
    /// <summary>
    /// 应用配置，集中管理服务器地址和端口
    /// 将 IP 和端口集中管理，便于部署时统一修改连接参数
    /// </summary>
    public static class AppConfig
    {
        // SSL 开关：true = 开启SSL(生产环境/Nginx), false = 关闭SSL(开发环境/直连)
        // 注意：关闭 SSL 连接后需要在Unity编辑器中开启HTTP开关
        public const bool USE_SSL = true;

        // 服务器 IP
        public const string SERVER_IP = "10.242.80.35";

        // ================= 自动计算配置 =================

        // HTTP 端口：SSL模式走 Nginx(443)，非SSL模式走 Tomcat/Jetty(8080)
        public static int HttpPort => USE_SSL ? 443 : 8080;

        // TCP 端口
        public const int TcpPort = 9999;

        // HTTP 协议头
        public static string HttpProtocol => USE_SSL ? "https" : "http";

        // 最终的基础 URL
        public static string ApiBaseUrl => $"{HttpProtocol}://{SERVER_IP}:{HttpPort}/api";

        // ================= 辅助方法：统一获取证书处理器 =================

        /// <summary>
        /// 根据 SSL 开关决定是否需要忽略证书错误
        /// </summary>
        public static CertificateHandler GetCertificateHandler()
        {
            if (USE_SSL)
            {
                // 如果开启了 SSL 且是自签名证书，挂载忽略器
                return new BypassCertificateHandler();
            }
            return null;
        }
    }
}