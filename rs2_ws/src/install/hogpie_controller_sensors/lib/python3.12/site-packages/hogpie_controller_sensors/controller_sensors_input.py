#!/usr/bin/env python3

import socket

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TcpServerNode(Node):

    def __init__(self):
        super().__init__('tcp_server_node')

        self.publisher_ = self.create_publisher(
            String,
            'tcp_data',
            10
        )

        self.host = '0.0.0.0'
        self.port = 5000

        self.get_logger().info(
            f'Starting TCP server on {self.host}:{self.port}'
        )

        self.run_server()

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1
            )

            server.bind((self.host, self.port))
            server.listen()

            while rclpy.ok():

                self.get_logger().info(
                    f'Listening on port {self.port}...'
                )

                try:
                    conn, addr = server.accept()

                    self.get_logger().info(
                        f'Client connected: {addr}'
                    )

                    with conn:

                        while rclpy.ok():

                            data = conn.recv(1024)

                            if not data:
                                self.get_logger().warn(
                                    'Client disconnected'
                                )
                                break

                            text = data.decode(
                                'utf-8',
                                errors='ignore'
                            ).strip()


                            msg = String()
                            msg.data = text
                            self.publisher_.publish(msg)

                except Exception as e:
                    self.get_logger().error(
                        f'Connection error: {e}'
                    )


def main(args=None):
    rclpy.init(args=args)

    try:
        node = TcpServerNode()
    except KeyboardInterrupt:
        pass

    rclpy.shutdown()


if __name__ == '__main__':
    main()