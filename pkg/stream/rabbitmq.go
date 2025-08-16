// Copyright Axis Communications AB.
//
// For a full list of individual contributors, please see the commit history.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package stream

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/rabbitmq/rabbitmq-stream-go-client/pkg/amqp"
	"github.com/rabbitmq/rabbitmq-stream-go-client/pkg/ha"
	"github.com/rabbitmq/rabbitmq-stream-go-client/pkg/message"
	"github.com/rabbitmq/rabbitmq-stream-go-client/pkg/stream"
)

const (
	IgnoreUnfiltered    = false
	MaxLengthBytes      = "2gb"
	MaxAge              = 10 * time.Second
	ConfirmationTimeout = 2 * time.Second
)

// RabbitMQStreamer is a struct representing a single RabbitMQ connection. From a new connection new streams may be
// created. Normal case is to have a single connection with multiple streams. If multiple connections are needed
// then multiple instances of the program should be run.
type RabbitMQStreamer struct {
	logger      *slog.Logger
	environment *stream.Environment
	streamName  string
}

// NewRabbitMQStreamer creates a new RabbitMQ streamer. Only a single connection should be created.
func NewRabbitMQStreamer(
	streamName string,
	address string,
	logger *slog.Logger,
) (Streamer, error) {
	options := stream.NewEnvironmentOptions().SetMaxProducersPerClient(1).SetUri(address)
	env, err := stream.NewEnvironment(options)
	if err != nil {
		return nil, err
	}
	return &RabbitMQStreamer{logger: logger, environment: env, streamName: streamName}, err
}

// CreateStream creates a new RabbitMQ stream.
func (s *RabbitMQStreamer) CreateStream(name string) error {
	// This will create the stream if not already created.
	return s.environment.DeclareStream(name,
		&stream.StreamOptions{
			MaxLengthBytes: stream.ByteCapacity{}.From(MaxLengthBytes),
			MaxAge:         MaxAge,
		},
	)
}

// Consumer returns a new Consumer.
func (s *RabbitMQStreamer) Consumer(name string) (Consumer, error) {
	exists, err := s.environment.StreamExists(s.streamName)
	if err != nil {
		return nil, err
	}
	if !exists {
		return nil, errors.New("no stream exists, cannot stream events")
	}
	options := stream.NewConsumerOptions().
		SetClientProvidedName(name).
		SetConsumerName(name).
		SetCRCCheck(false).
		SetOffset(stream.OffsetSpecification{}.First())
	return &RabbitMQStreamConsumer{
		logger:      s.logger,
		streamName:  s.streamName,
		environment: s.environment,
		options:     options,
	}, nil
}

// Publisher returns a new Publisher.
func (s *RabbitMQStreamer) Publisher(name string) (Publisher, error) {
	exists, err := s.environment.StreamExists(s.streamName)
	if err != nil {
		return nil, err
	}
	if !exists {
		return nil, errors.New("no stream exists, cannot stream events")
	}
	options := stream.NewProducerOptions().
		SetClientProvidedName(name).
		SetProducerName(name).
		SetConfirmationTimeOut(ConfirmationTimeout)
	return &RabbitMQStreamPublisher{
		logger:      s.logger,
		streamName:  s.streamName,
		environment: s.environment,
		options:     options,
	}, nil
}

// Close the RabbitMQ connection.
func (s *RabbitMQStreamer) Close() {
	err := s.environment.Close()
	if err != nil {
		s.logger.Error("failed to close RabbitMQStreamer", slog.Any("error", err))
	}
}

// RabbitMQStreamConsumer is a structure implementing the Consumer interface. Used to consume events
// from a RabbitMQ stream.
type RabbitMQStreamConsumer struct {
	ctx         context.Context
	logger      *slog.Logger
	streamName  string
	environment *stream.Environment
	options     *stream.ConsumerOptions
	consumer    *stream.Consumer
	channel     chan<- []byte
	filter      []string
}

// WithChannel adds a channel for receiving events from the stream. If no
// channel is added, then events will be logged.
func (s *RabbitMQStreamConsumer) WithChannel(ch chan<- []byte) Consumer {
	s.channel = ch
	return s
}

// WithOffset adds an offset to the RabbitMQ stream. -1 means start from the beginning.
func (s *RabbitMQStreamConsumer) WithOffset(offset int) Consumer {
	if offset == -1 {
		s.options = s.options.SetOffset(stream.OffsetSpecification{}.First())
	} else {
		s.options = s.options.SetOffset(stream.OffsetSpecification{}.Offset(int64(offset)))
	}
	return s
}

// WithFilter adds a filter to the RabbitMQ stream.
func (s *RabbitMQStreamConsumer) WithFilter(filter []string) Consumer {
	s.filter = filter
	if len(s.filter) > 0 {
		s.options = s.options.SetFilter(stream.NewConsumerFilter(filter, IgnoreUnfiltered, s.postFilter))
	}
	return s
}

// Consume will start consuming the RabbitMQ stream, non blocking. A channel is returned where
// an error is sent when the consumer closes down.
func (s *RabbitMQStreamConsumer) Consume() (<-chan error, error) {
	handler := func(_ stream.ConsumerContext, message *amqp.Message) {
		for _, d := range message.Data {
			if s.channel != nil {
				s.channel <- d
			} else {
				s.logger.Debug(string(d))
			}
		}
	}
	consumer, err := s.environment.NewConsumer(s.streamName, handler, s.options)
	if err != nil {
		return nil, err
	}
	s.consumer = consumer
	closed := make(chan error, 1)
	go s.notifyClose(s.ctx, closed)
	return closed, nil
}

// notifyClose will keep track of context and the notify close channel from RabbitMQ and send
// error on a channel.
func (s *RabbitMQStreamConsumer) notifyClose(ctx context.Context, ch chan<- error) {
	closed := s.consumer.NotifyClose()
	select {
	case <-ctx.Done():
		ch <- ctx.Err()
	case event := <-closed:
		ch <- event.Err
	}
}

// Close the RabbitMQ stream consumer.
func (s *RabbitMQStreamConsumer) Close() {
	if s.consumer != nil {
		if err := s.consumer.Close(); err != nil {
			s.logger.Error("failed to close rabbitmq consumer", slog.Any("error", err))
		}
	}
}

// postFilter applies client side filtering on all messages received from the RabbitMQ stream.
// The RabbitMQ server-side filtering is not perfect and will let through a few messages that don't
// match the filter, this is expected as the RabbitMQ unit of delivery is the chunk and there may
// be multiple messages in a chunk and those messages are not filtered.
func (s *RabbitMQStreamConsumer) postFilter(message *amqp.Message) bool {
	if s.filter == nil {
		return true // Unfiltered
	}
	identifier := message.ApplicationProperties["identifier"]
	eventType := message.ApplicationProperties["type"]
	eventMeta := message.ApplicationProperties["meta"]
	name := fmt.Sprintf("%s.%s.%s", identifier, eventType, eventMeta)
	for _, filter := range s.filter {
		if name == filter {
			return true
		}
	}
	return false
}

// RabbitMQStreamPublisher is a structure implementing the Publisher interface. Used to publish events
// to a RabbitMQ stream.
type RabbitMQStreamPublisher struct {
	logger              *slog.Logger
	streamName          string
	environment         *stream.Environment
	options             *stream.ProducerOptions
	producer            *ha.ReliableProducer
	unConfirmedMessages chan message.StreamMessage
	unConfirmed         *sync.WaitGroup
	done                chan struct{}
	shutdown            bool
}

type Filter struct {
	Identifier string
	Type       string
	Meta       string
}

// Start will start the RabbitMQ stream publisher, non blocking. A channel is returned where
// a events can be published.
func (s *RabbitMQStreamPublisher) Start() error {
	// TODO: Make a 'New' function
	s.unConfirmed = &sync.WaitGroup{}
	// TODO: Verify if unlimited is good or bad.
	s.unConfirmedMessages = make(chan message.StreamMessage)
	s.options.SetFilter(stream.NewProducerFilter(func(message message.StreamMessage) string {
		p := message.GetApplicationProperties()
		return fmt.Sprintf("%s.%s.%s", p["identifier"], p["type"], p["meta"])
	}))
	producer, err := ha.NewReliableProducer(
		s.environment,
		s.streamName,
		s.options,
		func(messageStatus []*stream.ConfirmationStatus) {
			go func() {
				for _, msgStatus := range messageStatus {
					if msgStatus.IsConfirmed() {
						s.unConfirmed.Done()
					} else {
						s.logger.Warn("Unconfirmed message", slog.Any("error", msgStatus.GetError()))
						s.unConfirmedMessages <- msgStatus.GetMessage()
					}
				}
			}()
		})
	if err != nil {
		return err
	}
	s.producer = producer
	s.done = make(chan struct{})
	go s.publish(s.done)
	return nil
}

// Publish an event to the RabbitMQ stream.
func (s *RabbitMQStreamPublisher) Publish(msg []byte, filter Filter) {
	if s.shutdown {
		s.logger.Error("Publisher is closed")
		return
	}
	s.unConfirmed.Add(1)
	message := amqp.NewMessage(msg)
	if filter.Meta == "" {
		filter.Meta = "*"
	}
	message.ApplicationProperties = map[string]interface{}{
		"identifier": filter.Identifier,
		"type":       filter.Type,
		"meta":       filter.Meta,
	}
	s.unConfirmedMessages <- message
}

// publish a message from unconfirmed messages to RabbitMQ.
func (s *RabbitMQStreamPublisher) publish(done chan struct{}) {
	for {
		select {
		case msg := <-s.unConfirmedMessages:
			if err := s.producer.Send(msg); err != nil {
				s.logger.Error("Failed to send message", slog.Any("error", err))
			}
		case <-done:
			return
		}
	}
}

// Close the RabbitMQ stream publisher.
func (s *RabbitMQStreamPublisher) Close() {
	if s.producer != nil {
		s.logger.Info("Stopping publisher")
		s.shutdown = true
		s.logger.Info("Wait for unconfirmed messages")
		s.unConfirmed.Wait()
		s.done <- struct{}{}
		s.logger.Info("Done, closing down")
		if err := s.producer.Close(); err != nil {
			s.logger.Error("Failed to close rabbitmq publisher", slog.Any("error", err))
		}
		close(s.unConfirmedMessages)
	}
}
