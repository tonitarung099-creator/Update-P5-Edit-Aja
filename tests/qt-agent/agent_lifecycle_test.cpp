// SPDX-License-Identifier: GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
#include "openaicompatibleagent.h"
#include "agenttoolregistry.h"
#include <QHostAddress>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QSignalSpy>
#include <QTcpServer>
#include <QTcpSocket>
#include <QtTest>

// Real local HTTP, no credentials or remote API. Hold replies until the test
// chooses to finish, so duplicate and cancel/restart races are deterministic.
class HttpFixture : public QObject
{
public:
    QTcpServer server;
    QList<QPointer<QTcpSocket>> requests;
    HttpFixture()
    {
        connect(&server, &QTcpServer::newConnection, this, [this]() {
            while (server.hasPendingConnections()) {
                auto *socket = server.nextPendingConnection();
                connect(socket, &QTcpSocket::readyRead, this, [this, socket]() {
                    auto data = socket->property("request").toByteArray() + socket->readAll();
                    socket->setProperty("request", data);
                    if (!socket->property("counted").toBool() && data.contains("\r\n\r\n")) {
                        socket->setProperty("counted", true);
                        requests.append(socket);
                    }
                });
            }
        });
    }
    QString url() const { return QStringLiteral("http://127.0.0.1:%1/v1/chat/completions").arg(server.serverPort()); }
    void respond(int index, const QByteArray &body)
    {
        auto socket = requests.at(index);
        if (!socket || socket->state() != QAbstractSocket::ConnectedState) return;
        socket->write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: "
                      + QByteArray::number(body.size()) + "\r\n\r\n" + body);
        socket->disconnectFromHost();
    }
};

class AgentLifecycleTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void duplicateDoesNotUnlockActiveRequest()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("fixture"), {});
        QSignalSpy busy(&agent, &OpenAiCompatibleAgent::busyChanged);
        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        QSignalSpy finished(&agent, &OpenAiCompatibleAgent::finished);
        agent.run(QStringLiteral("first"), false);
        QTRY_COMPARE(http.requests.size(), 1);
        agent.run(QStringLiteral("duplicate"), false);
        QCOMPARE(failed.size(), 1); // rejected duplicate, not failed active run
        QCOMPARE(busy.size(), 1);
        QVERIFY(busy.at(0).at(0).toBool());
        http.respond(0, R"({"choices":[{"message":{"role":"assistant","content":"first completed"}}]})");
        QTRY_COMPARE(finished.size(), 1);
        QCOMPARE(finished.at(0).at(0).toString(), QStringLiteral("first completed"));
        QCOMPARE(http.requests.size(), 1);
        QCOMPARE(busy.size(), 2);
        QVERIFY(!busy.last().at(0).toBool());
    }
    void cancelThenRestartDoesNotReportStaleFailure()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("fixture"), {});
        QSignalSpy busy(&agent, &OpenAiCompatibleAgent::busyChanged);
        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        QSignalSpy finished(&agent, &OpenAiCompatibleAgent::finished);
        agent.run(QStringLiteral("cancel this"), false);
        QTRY_COMPARE(http.requests.size(), 1);
        agent.cancel();
        QCOMPARE(failed.size(), 0);
        QCOMPARE(finished.size(), 0);
        agent.cancel(); // repeated cancellation must be harmless
        agent.run(QStringLiteral("next"), false);
        QTRY_COMPARE(http.requests.size(), 2);
        QVERIFY(busy.last().at(0).toBool());
        http.respond(0, R"({"choices":[{"message":{"role":"assistant","content":"stale"}}]})");
        http.respond(1, R"({"choices":[{"message":{"role":"assistant","content":"next completed"}}]})");
        QTRY_COMPARE(finished.size(), 1);
        QCOMPARE(finished.at(0).at(0).toString(), QStringLiteral("next completed"));
        QCOMPARE(failed.size(), 0);
        QVERIFY(!busy.last().at(0).toBool());
    }
    void genuineApiFailureStillRestoresIdle()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("fixture"), {});
        QSignalSpy busy(&agent, &OpenAiCompatibleAgent::busyChanged);
        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        agent.run(QStringLiteral("invalid JSON fixture"), false);
        QTRY_COMPARE(http.requests.size(), 1);
        http.respond(0, "not JSON");
        QTRY_COMPARE(failed.size(), 1);
        QVERIFY(!busy.last().at(0).toBool());
        QVERIFY(failed.at(0).at(0).toString().contains(QStringLiteral("invalid JSON")));
    }
};
QTEST_GUILESS_MAIN(AgentLifecycleTest)
#include "agent_lifecycle_test.moc"
