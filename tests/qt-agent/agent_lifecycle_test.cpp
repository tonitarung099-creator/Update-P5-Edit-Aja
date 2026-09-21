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
#include <QTimer>
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
    QByteArray requestData(int index) const
    {
        auto socket = requests.at(index);
        return socket ? socket->property("request").toByteArray() : QByteArray{};
    }
    void respondStatus(int index, int status, const QByteArray &body, const QByteArray &extraHeaders = {})
    {
        auto socket = requests.at(index);
        if (!socket || socket->state() != QAbstractSocket::ConnectedState) return;
        const QByteArray reason = status == 200 ? " OK" : status == 429 ? " Too Many Requests" : " Error";
        socket->write("HTTP/1.1 " + QByteArray::number(status) + reason
                      + "\r\nContent-Type: application/json\r\nConnection: close\r\n"
                      + extraHeaders
                      + "Content-Length: " + QByteArray::number(body.size()) + "\r\n\r\n" + body);
        socket->disconnectFromHost();
    }
    void respond(int index, const QByteArray &body)
    {
        respondStatus(index, 200, body);
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
    void stalledApiRequestTimesOutAndNextRunSucceeds()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("fixture"), {});
        agent.setRequestTimeoutMs(80);

        QSignalSpy busy(&agent, &OpenAiCompatibleAgent::busyChanged);
        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        QSignalSpy finished(&agent, &OpenAiCompatibleAgent::finished);

        agent.run(QStringLiteral("never respond"), false);
        QTRY_COMPARE(http.requests.size(), 1);
        QTRY_COMPARE(failed.size(), 1);
        QVERIFY(failed.at(0).at(0).toString().contains(QStringLiteral("timed out")));
        QVERIFY(!busy.last().at(0).toBool());
        QCOMPARE(finished.size(), 0);

        // The aborted reply may finish after the timeout. It must be stale and
        // must not emit a second failure or change the next request's state.
        QTest::qWait(120);
        QCOMPARE(failed.size(), 1);

        agent.setRequestTimeoutMs(1000);
        agent.run(QStringLiteral("fresh after timeout"), false);
        QTRY_COMPARE(http.requests.size(), 2);
        QVERIFY(busy.last().at(0).toBool());
        http.respond(1, R"json({"choices":[{"message":{"role":"assistant","content":"fresh after timeout completed"}}]})json");
        QTRY_COMPARE(finished.size(), 1);
        QCOMPARE(finished.at(0).at(0).toString(), QStringLiteral("fresh after timeout completed"));
        QCOMPARE(failed.size(), 1);
        QVERIFY(!busy.last().at(0).toBool());
    }

    void cancelStopsPendingRequestTimeout()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("fixture"), {});
        agent.setRequestTimeoutMs(80);

        QSignalSpy busy(&agent, &OpenAiCompatibleAgent::busyChanged);
        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        agent.run(QStringLiteral("cancel before timeout"), false);
        QTRY_COMPARE(http.requests.size(), 1);
        agent.cancel();
        QTest::qWait(140);

        QCOMPARE(failed.size(), 0);
        QVERIFY(!busy.last().at(0).toBool());
    }
    void geminiQuotaRotatesToNextKey()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("gemini-fixture"), QStringLiteral("key-a\nkey-b"));
        agent.setProperty("p5GeminiOnly", true);
        agent.setProperty("p5GeminiKeyIndex", 0);

        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        QSignalSpy finished(&agent, &OpenAiCompatibleAgent::finished);
        QSignalSpy trace(&agent, &OpenAiCompatibleAgent::trace);

        agent.run(QStringLiteral("rotate on quota"), false);
        QTRY_COMPARE(http.requests.size(), 1);
        QVERIFY(http.requestData(0).toLower().contains("authorization: bearer key-a"));

        http.respondStatus(
            0,
            429,
            R"json({"error":{"status":"RESOURCE_EXHAUSTED","message":"quota exceeded"}})json",
            "Retry-After: 60\r\n");
        QTRY_COMPARE(http.requests.size(), 2);
        QVERIFY(http.requestData(1).toLower().contains("authorization: bearer key-b"));

        bool sawSwitch = false;
        for (const auto &entry : trace) {
            if (entry.at(0).toString().contains(QStringLiteral("Switching automatically to Gemini key 2/2"))) {
                sawSwitch = true;
                break;
            }
        }
        QVERIFY(sawSwitch);

        http.respond(1, R"json({"choices":[{"message":{"role":"assistant","content":"rotated success"}}]})json");
        QTRY_COMPARE(finished.size(), 1);
        QCOMPARE(finished.at(0).at(0).toString(), QStringLiteral("rotated success"));
        QCOMPARE(failed.size(), 0);
    }

    void asyncToolKeepsEventLoopResponsiveAndCompletesAgent()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        int toolStarts = 0;
        registry.registerAsyncTool(
            QStringLiteral("slow_fixture"),
            QStringLiteral("Delayed local fixture"),
            QJsonObject{{QStringLiteral("type"), QStringLiteral("object")}},
            [&registry, &toolStarts](const QJsonObject &, AgentToolRegistry::Completion completion) {
                ++toolStarts;
                auto *timer = new QTimer(&registry);
                timer->setSingleShot(true);
                QPointer<QTimer> guard(timer);
                QObject::connect(timer, &QTimer::timeout, &registry, [guard, completion]() {
                    if (!guard) {
                        return;
                    }
                    completion(QJsonObject{{QStringLiteral("ok"), true}, {QStringLiteral("value"), QStringLiteral("async done")}});
                    guard->deleteLater();
                });
                timer->start(180);
                return [guard]() {
                    if (guard) {
                        guard->stop();
                        guard->deleteLater();
                    }
                };
            });

        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("fixture"), {});
        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        QSignalSpy finished(&agent, &OpenAiCompatibleAgent::finished);
        agent.run(QStringLiteral("use slow fixture"), false);
        QTRY_COMPARE(http.requests.size(), 1);

        QTimer heartbeat;
        int heartbeatTicks = 0;
        QObject::connect(&heartbeat, &QTimer::timeout, this, [&heartbeatTicks]() { ++heartbeatTicks; });
        heartbeat.start(10);
        http.respond(0, R"json({"choices":[{"message":{"role":"assistant","content":"","tool_calls":[{"id":"call-async","type":"function","function":{"name":"slow_fixture","arguments":"{}"}}]}}]})json");
        QTRY_COMPARE(toolStarts, 1);
        const int ticksAtStart = heartbeatTicks;
        QTRY_VERIFY(heartbeatTicks >= ticksAtStart + 5);
        QCOMPARE(http.requests.size(), 1);
        QTRY_COMPARE(http.requests.size(), 2);
        heartbeat.stop();
        QVERIFY(heartbeatTicks >= ticksAtStart + 5);

        http.respond(1, R"json({"choices":[{"message":{"role":"assistant","content":"async completed"}}]})json");
        QTRY_COMPARE(finished.size(), 1);
        QCOMPARE(finished.at(0).at(0).toString(), QStringLiteral("async completed"));
        QCOMPARE(failed.size(), 0);
    }

    void cancelAsyncToolThenRestartDoesNotLeakCompletion()
    {
        HttpFixture http;
        QVERIFY(http.server.listen(QHostAddress::LocalHost, 0));
        AgentToolRegistry registry;
        int toolStarts = 0;
        int toolCancels = 0;
        registry.registerAsyncTool(
            QStringLiteral("slow_fixture"),
            QStringLiteral("Cancellable delayed fixture"),
            QJsonObject{{QStringLiteral("type"), QStringLiteral("object")}},
            [&registry, &toolStarts, &toolCancels](const QJsonObject &, AgentToolRegistry::Completion completion) {
                ++toolStarts;
                auto *timer = new QTimer(&registry);
                timer->setSingleShot(true);
                QPointer<QTimer> guard(timer);
                QObject::connect(timer, &QTimer::timeout, &registry, [guard, completion]() {
                    if (!guard) {
                        return;
                    }
                    completion(QJsonObject{{QStringLiteral("ok"), true}, {QStringLiteral("value"), QStringLiteral("stale completion")}});
                    guard->deleteLater();
                });
                timer->start(500);
                return [guard, &toolCancels]() {
                    ++toolCancels;
                    if (guard) {
                        guard->stop();
                        guard->deleteLater();
                    }
                };
            });

        OpenAiCompatibleAgent agent(&registry);
        agent.configure(http.url(), QStringLiteral("fixture"), {});
        QSignalSpy failed(&agent, &OpenAiCompatibleAgent::failed);
        QSignalSpy finished(&agent, &OpenAiCompatibleAgent::finished);

        agent.run(QStringLiteral("start cancellable tool"), false);
        QTRY_COMPARE(http.requests.size(), 1);
        http.respond(0, R"json({"choices":[{"message":{"role":"assistant","content":"","tool_calls":[{"id":"call-cancel","type":"function","function":{"name":"slow_fixture","arguments":"{}"}}]}}]})json");
        QTRY_COMPARE(toolStarts, 1);
        agent.cancel();
        QCOMPARE(toolCancels, 1);
        QTest::qWait(600);
        QCOMPARE(http.requests.size(), 1);
        QCOMPARE(failed.size(), 0);
        QCOMPARE(finished.size(), 0);

        agent.run(QStringLiteral("fresh request"), false);
        QTRY_COMPARE(http.requests.size(), 2);
        http.respond(1, R"json({"choices":[{"message":{"role":"assistant","content":"fresh completed"}}]})json");
        QTRY_COMPARE(finished.size(), 1);
        QCOMPARE(finished.at(0).at(0).toString(), QStringLiteral("fresh completed"));
        QCOMPARE(failed.size(), 0);
    }
};
QTEST_GUILESS_MAIN(AgentLifecycleTest)
#include "agent_lifecycle_test.moc"
